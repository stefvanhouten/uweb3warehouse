#!/usr/bin/python3
"""Database abstraction model for the warehouse."""

__author__ = "Jan Klopper <janklopper@underdark.nl>"
__version__ = "1.0"

import datetime
import decimal
import math

# standard modules
from dataclasses import dataclass

import pytz
import uweb3.helpers
from uweb3 import model

from warehouse.common import model as common_model


class AssemblyError(common_model.WarehouseException):
    """The requested operation cannot continue because we could not assemble a
    product as requested."""


@dataclass
class ProductPiecePrice:
    piece_price: decimal.Decimal
    leftover_stock: int


class Product(model.Record):
    """Provides a model abstraction for the Product table"""

    _possiblestock = None
    _parts = None
    _products = None

    @classmethod
    def Create(self, connection, record):
        sku = record.get("sku")
        if not sku:
            raise KeyError("Product must have a SKU value.")
        try:
            self.FromSku(connection, sku, check_deleted=True)
        except self.NotExistError:
            pass
        else:
            raise self.AlreadyExistError(f"Product with SKU {sku} already exists.")
        return super().Create(connection, record)

    @classmethod
    def List(cls, connection, conditions=[], *args, **kwargs):
        """Returns the Products filtered on not deleted"""
        return super().List(
            connection,
            conditions=[common_model.NOTDELETED] + conditions,
            *args,
            **kwargs,
        )

    @classmethod
    def Search(cls, connection, query=None, order=None, conditions=None, **kwargs):
        """Returns the products matching the search

        Arguments:
        @ connection: sqltalk.connection
            Database connection to use.
        % query: str
            Filters on name
        """
        if not conditions:
            conditions = []
        queryorder = [("product.dateCreated", True)]
        if order:
            queryorder = order + queryorder
        return cls.List(
            connection,
            conditions=['name like "%%%s%%"' % connection.EscapeValues(query)[1:-1]]
            + conditions,
            order=queryorder,
            **kwargs,
        )

    @classmethod
    def FromSku(cls, connection, sku, conditions=None, check_deleted=False):
        """Returns the product of the given common name.

        Arguments:
            @ connection: sqltalk.connection
                Database connection to use.
            @ name: str
                The common name of the product.
            @ check_deleted: bool
                If true return the deleted product if it exists.
        Raises:
            NotExistError:
                The given product name does not exist.

        Returns:
            Collection: product abstraction class.
        """
        if not conditions:
            conditions = []
        safe_sku = connection.EscapeValues(sku)
        conditions.append("sku=%s" % safe_sku)

        if not check_deleted:
            conditions.append(common_model.NOTDELETED)

        with connection as cursor:
            product = cursor.Select(
                table=cls.TableName(),
                conditions=conditions,
            )
        if not product:
            raise cls.NotExistError(f"There is no product with sku {sku}")
        return cls(connection, product[0])

    def Delete(self):
        """Overwrites the default Delete and sets the dateDeleted datetime instead"""
        self["dateDeleted"] = str(pytz.utc.localize(datetime.datetime.utcnow()))[0:19]
        self.Save()

    def _PreCreate(self, cursor):
        super()._PreCreate(cursor)
        self._Noramlize()

    def _PreSave(self, cursor):
        super()._PreSave(cursor)
        self._Noramlize()

    def _Noramlize(self):
        if self["name"]:
            self["name"] = self["name"].replace("/", "_")
        if not self["gs1"]:  # set empty string to None for key contraints
            self["gs1"] = None
        if not self["name"]:
            raise common_model.InvalidNameError("Provide a valid name")

    @property
    def parts(self):
        """List products used as parts for this product"""
        if self._parts is None:
            self._parts = list(self._Children(Productpart))
        return self._parts

    @property
    def products(self):
        """List products that use this product as a part"""
        if self._products is None:
            self._products = list(self._Children(Productpart, relation_field="part"))
        return self._products

    def Stock(self, *args, **kwargs):
        """List stock changes for this product"""
        return self._Children(Stock, *args, **kwargs)

    @property
    def currentstock(self):
        """Returns the current stock"""
        with self.connection as cursor:
            stock = cursor.Select(
                table=Stock.TableName(),
                fields="sum(amount) as currentstock",
                conditions=["product=%d" % self.key],
                escape=False,
            )
        if stock[0]["currentstock"]:
            return int(stock[0]["currentstock"])
        return 0

    @property
    def product_stock_prices(self):
        """Returns the piece_price and the amount of leftovers of the stock for that price."""
        # TODO: Handle negative stock, how do we determine the price?
        with self.connection as cursor:
            results = cursor.Execute(
                f"""
                SELECT
                    parent.piece_price,
                    parent.amount,
                    (select sum(test.amount) from warehouse.stock as test where product={self['ID']} and piece_price is not null and test.ID <= parent.ID) +
                    (select coalesce(sum(test.amount), 0) from warehouse.stock as test where product={self['ID']} and piece_price is null) as actual_leftover_stock
                FROM warehouse.stock as parent
                WHERE product={self['ID']}
                AND piece_price is not null
                AND (select sum(test.amount) from warehouse.stock as test where product={self['ID']} and piece_price is not null and test.ID <= parent.ID) +
                (select coalesce(sum(test.amount), 0) from warehouse.stock as test where product={self['ID']} and piece_price is null) >= 1;
                """
            )
        prv = 0
        lst = []
        for row in results:
            lst.append(
                ProductPiecePrice(
                    row["piece_price"], row["actual_leftover_stock"] - prv
                )
            )
            prv = row["actual_leftover_stock"]
        return lst

    @property
    def possiblestock(
        self,
    ):  # XXX: This is actually not the possiblestock, this is the possible addition to the stock. currentstock + possiblestock['available'] = possiblestock.
        """Returns the possible stock when using up currently available parts"""
        if self._possiblestock:
            return self._possiblestock

        parts = list(self.parts)
        if not parts:
            self._possiblestock = {
                "available": 0,
                "parts": None,
                "limitedby": None,
            }
            return self._possiblestock

        limitedby = parts[0]
        availableassemblies = math.inf

        for part in parts:
            part["availablestock"] = part["part"].currentstock
            part["availablepossiblestock"] = part["part"].possiblestock

            if part["amount"]:
                part["availableassemblies"] = int(
                    (
                        part["availablestock"]
                        + part["availablepossiblestock"]["available"]
                    )
                    / part["amount"]
                )
                if part["availableassemblies"] < availableassemblies:
                    limitedby = part
                availableassemblies = min(
                    availableassemblies, part["availableassemblies"]
                )

        self._possiblestock = {
            "available": availableassemblies if availableassemblies >= 0 else 0,
            "parts": parts,
            "limitedby": limitedby,
        }
        return self._possiblestock

    def AssemblyPossible(self, amount):
        possiblestock = self.possiblestock
        if not possiblestock["available"] and not possiblestock["limitedby"]:
            raise AssemblyError(
                "Cannot assemble this product, is not an assembled product."
            )
        if not possiblestock["available"] or possiblestock["available"] < amount:
            raise AssemblyError(
                "Cannot assemble this product, not enough parts. Limited by: %s"
                % possiblestock["limitedby"]["part"]["sku"]
            )
        return possiblestock["parts"]

    def DisassemblyPossible(self, amount):
        if self.currentstock < amount:
            raise AssemblyError(
                "Cannot Disassemble this product, not enough stock available."
            )
        parts = list(self.parts)
        if not parts:
            raise AssemblyError(
                "Cannot Disassemble this product, is not an assembled product."
            )
        return parts

    def Disassemble(self, amount=1, reference="Disassembled for parts", lot=None):
        """Remove as many assemblies as requested and create stock for parts"""
        parts = self.DisassemblyPossible(amount)

        with uweb3.helpers.transaction(self.connection, self.__class__):
            for part in parts:
                self._ManageDisassemblyFromParts(amount, part)

            return Stock.Create(
                self.connection,
                {
                    "product": self.key,
                    "amount": amount * -1,
                    "reference": reference,
                    "lot": lot,
                },
            )

    def _ManageDisassemblyFromParts(self, amount, part):
        """Determines the price of the part that this product is disassembled to.
        The price is determined based on the most recent stock piece price.

        Args:
            amount (int): The amount of parts to disassemble
            part (model.Productpart): The ProductPart record to disassemble from.

        Returns:
            model.Stock: The newly created stock record.
        """
        piece_price = self._CalculateDisassemblyPrice(part["part"])
        return Stock.Create(
            self.connection,
            {
                "product": part["part"]["ID"],
                "amount": amount * part["amount"],
                "reference": f"Disassembly: {part['product']['name']}, amount: {amount}",
                "piece_price": piece_price,
            },
        )

    def _CalculateDisassemblyPrice(self, part):
        """Retrieve the most recent piece price for this part.
        If no price could be found because there is no stock present for a given product
        the piece price is returned as decimal 0.

        Args:
            part (model.Product): The ProductPart record to disassemble from.

        Raises:
            AssemblyError: Raised when no recent product price could be found from the stock.

        Returns:
            decimal.Decimal: The piece price for each part, or decimal 0 if no price is found.
        """
        latest_price = list(
            Stock.List(
                self.connection,
                conditions=(
                    f'product={part["ID"]}',
                    "piece_price is not null",
                ),
                limit=1,
                order=[("ID", True)],
            )
        )
        if not latest_price:
            return decimal.Decimal(0)
        return latest_price[0]["piece_price"]

    def Assemble(self, amount=1, reference="Assembled from parts", lot=None):
        """Tries to use up this products parts and assembles them, mutating stock on all products involved."""
        parts = self.AssemblyPossible(amount)
        # Mutate parts one by one
        price = decimal.Decimal(0)
        with uweb3.helpers.transaction(self.connection, self.__class__):
            for part in parts:
                price += self._ManageAssemblyFromParts(amount, part)

            return Stock.Create(
                self.connection,
                {
                    "product": self.key,
                    "amount": amount,
                    "reference": reference,
                    "lot": lot,
                    "piece_price": price,
                },
            )

    def _ManageAssemblyFromParts(self, amount, part):
        """Assembles a part from stock, using the piece prices of the stock to determine how much
        an assembled part cost.

        Args:
            amount (int): The amount of parts to assemble, this is not the amount of pieces in the assembled product.
                            For example, if you have a product with 3 parts and you want to assemble 2 of them,
                            amount will be 2.
            part (model.Productpart): The ProductPart that we want to assemble.

        Returns:
            decimal.Decimal: The price of the assembled product.
        """

        price = self._CalculateAssemblyPrice(amount, part)
        self._AssembleFromParts(amount, part)
        return price

    def _CalculateAssemblyPrice(self, amount, part):
        """Calculate the total price of assembly for a part based on the current stock, and the prices the stock was bought at.

        Args:
            part (model.Productpart): The ProductPart that we want to assemble.
            amount (int): The amount of products that we want to assemble.

        Returns:
            decimal.Decimal: The cost of assembly for each individual product.
        """
        stock_info = part["part"].product_stock_prices
        parts_needed_for_assembly = part["amount"]
        pieces_needed = parts_needed_for_assembly * amount

        price = decimal.Decimal(0)
        current_pieces_used = 0
        for pair in stock_info:
            if (current_pieces_used + pair.leftover_stock) <= pieces_needed:
                current_pieces_used += pair.leftover_stock
                price += pair.piece_price * pair.leftover_stock
                pair.leftover_stock = 0
            else:
                parts_needed = pieces_needed - current_pieces_used
                price += pair.piece_price * parts_needed
                pair.leftover_stock -= parts_needed
                current_pieces_used += parts_needed
        return decimal.Decimal(price / amount)

    def _AssembleFromParts(self, amount, part):
        subreference = "Assembly: %s, amount: %s " % (self["name"], amount)
        Stock.Create(
            self.connection,
            {
                "product": int(part["part"]),
                "amount": (part["amount"] * amount) * -1,
                "reference": subreference,
            },
        )

    def AssemblyOptions(self):
        partIds = []
        for part in self.parts:
            partIds.append(str(int(part["part"])))

        return self.List(
            self.connection,
            conditions=[
                "ID != %d" % self.key,
                "ID not in (%s)" % ",".join(partIds) if partIds else "true",
            ],
        )

    @property
    def Eancode(self):
        if self["ean"]:
            return self["ean"]
        if self["gs1"]:
            try:
                return "%d%03d" % (
                    int(self["supplier"]["gscode"]),
                    self["gs1"],
                )
            except (KeyError, ValueError):
                return None
        return None

    @property
    def cost(self):
        """Returns the current cost of a single product, this price is dynamic and depends on the
        currently available stock. This is the price that is used when the product is sold.

        Returns:
            decimal.Decimal: The current price for a single product depending on stock
        """
        return self._CalculateDisassemblyPrice(self)


class Stock(model.Record):
    """Provides a model abstraction for the stock table"""


class Productpart(model.Record):
    """Provides a model abstraction for the Productpart table"""

    _FOREIGN_RELATIONS = {"part": Product}

    @property
    def subtotal(self):
        return self["amount"] * self["part"].cost


class Productprice(model.Record):
    """Provides a model abstraction for the Productprice table"""

    @classmethod
    def ProductPrices(cls, connection, product):
        return cls.List(connection, conditions=[f"product={product['ID']}"])
