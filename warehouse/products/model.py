#!/usr/bin/python3
"""Database abstraction model for the warehouse."""

__author__ = "Jan Klopper <janklopper@underdark.nl>"
__version__ = "1.0"

# standard modules
import datetime
import math

import pytz
from uweb3 import model

from warehouse.common import model as common_model
from warehouse.login import model as login_model


class Product(model.Record):
    """Provides a model abstraction for the Product table"""

    _possiblestock = None
    _parts = None
    _products = None

    @classmethod
    def List(cls, connection, conditions=[], *args, **kwargs):
        """Returns the Products filtered on not deleted"""
        return super().List(
            connection,
            conditions=[common_model.NOTDELETED] + conditions,
            *args,
            **kwargs
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
            **kwargs
        )

    @classmethod
    def FromName(cls, connection, name, conditions=None):
        """Returns the product of the given common name.

        Arguments:
          @ connection: sqltalk.connection
            Database connection to use.
          @ name: str
            The common name of the product.

        Raises:
          NotExistError:
            The given product name does not exist.

        Returns:
          Collection: product abstraction class.
        """
        if not conditions:
            conditions = []
        safe_name = connection.EscapeValues(name)
        with connection as cursor:
            product = cursor.Select(
                table=cls.TableName(),
                conditions=["name=%s" % safe_name, common_model.NOTDELETED]
                + conditions,
            )
        if not product:
            raise cls.NotExistError("There is no product with common name %r" % name)
        return cls(connection, product[0])

    def Delete(self):
        """Overwrites the default Delete and sets the dateDeleted datetime instead"""
        self["dateDeleted"] = str(pytz.utc.localize(datetime.datetime.utcnow()))[0:19]
        self.Save()

    def _PreCreate(self, cursor):
        super()._PreCreate(cursor)
        if self["name"]:
            self["name"] = self["name"].replace("/", "_")
        #     self["name"] = re.search(
        #         "([\w\-_\.,]+)", self["name"].replace(" ", "_")
        #     ).groups()[0][:255]
        if not self["gs1"]:  # set empty string to None for key contraints
            self["gs1"] = None
        if not self["sku"]:  # set empty string to None for key contraints
            self["sku"] = None
        if not self["name"]:
            raise common_model.InvalidNameError("Provide a valid name")

    def _PreSave(self, cursor):
        super()._PreSave(cursor)
        if self["name"]:
            self["name"] = self["name"].replace("/", "_")
        #     self["name"] = re.search(
        #         "([\w\-_\.,]+)", self["name"].replace(" ", "_")
        #     ).groups()[0][:255]
        if not self["gs1"]:  # set empty string to None for key contraints
            self["gs1"] = None
        if not self["sku"]:  # set empty string to None for key contraints
            self["sku"] = None
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
    def possiblestock(
        self,
    ):  # XXX: This is actually not the possiblestock, this is the possible addition to the stock. currentstock + possiblestock['available'] = possiblestock.
        """Returns the possible stock when using up currently available parts"""
        if self._possiblestock:
            return self._possiblestock

        parts = list(self.parts)
        if not parts:
            self._possiblestock = {"available": 0, "parts": None, "limitedby": None}
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
            "available": availableassemblies,
            "parts": parts,
            "limitedby": limitedby,
        }
        return self._possiblestock

    def AssemblyPossible(self, amount):
        if amount > 0:
            possiblestock = self.possiblestock
            if not possiblestock["available"] and not possiblestock["limitedby"]:
                raise common_model.AssemblyError(
                    "Cannot assemble this product, is not an assembled product."
                )
            if not possiblestock["available"] or possiblestock["available"] < amount:
                raise common_model.AssemblyError(
                    "Cannot assemble this product, not enough parts. Limited by: %s"
                    % possiblestock["limitedby"]["part"]["name"]
                )
            parts = possiblestock["parts"]
        elif amount < 0:
            if self.currentstock < abs(amount):
                raise common_model.AssemblyError(
                    "Cannot Disassemble this product, not enough stock available."
                )
            parts = list(self.parts)
            if parts == 0:
                raise common_model.AssemblyError(
                    "Cannot Disassemble this product, is not an assembled product."
                )
        return parts

    def Assemble(self, amount=1, reference="Assembled from parts", lot=None):
        """Tries to use up this products parts and assembles them, mutating stock on all products involved."""
        parts = self.AssemblyPossible(amount)
        # Mutate parts one by one
        for part in parts:
            subreference = "Assembly: %s, %s" % (self["name"], reference)
            Stock.Create(
                self.connection,
                {
                    "product": int(part["part"]),
                    "amount": (part["amount"] * amount) * -1,
                    "reference": subreference[0:45],
                },
            )
        # Mutate this product as requested
        return Stock.Create(
            self.connection,
            {
                "product": self.key,
                "amount": amount,
                "reference": reference[0:45] if reference else "",
                "lot": lot,
            },
        )

    def Disassemble(self, amount=1, reference="Disassembled for parts", lot=None):
        """Remove as many assemblies as requested and create stock for parts"""
        return self.Assemble(amount * -1, reference or "Disassembled for parts", lot)

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
                return "%d%03d" % (int(self["supplier"]["gscode"]), self["gs1"])
            except (KeyError, ValueError):
                return None
        return None


class Stock(model.Record):
    """Provides a model abstraction for the stock table"""


class Productpart(model.Record):
    """Provides a model abstraction for the Productpart table"""

    _FOREIGN_RELATIONS = {"part": Product}

    @property
    def subtotal(self):
        return (self["amount"] * self["part"]["cost"]) + self["assemblycosts"]
