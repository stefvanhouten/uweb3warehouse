#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

import os
import urllib.parse

import uweb3

from warehouse import basepages
from warehouse.common import model as common_model
from warehouse.common.decorators import NotExistsErrorCatcher, loggedin
from warehouse.common.helpers import PagedResult
from warehouse.login import model as login_model
from warehouse.products import forms, model
from warehouse.suppliers import model as supplier_model


class PageMaker(basepages.PageMaker):

    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

    @loggedin
    @uweb3.decorators.TemplateParser("products.html")
    def RequestProducts(self, product_form=None):
        """Returns the Products page"""
        if not product_form:
            product_form = forms.ProductForm()

        supplier = None
        conditions = []
        linkarguments = {}
        if "supplier" in self.get:
            try:
                supplier = supplier_model.Supplier.FromPrimary(
                    self.connection, self.get.getfirst("supplier", None)
                )
                conditions.append("supplier = %d" % supplier)
                linkarguments["supplier"] = int(supplier)
            except login_model.User.NotExistError:
                pass

        products_args = {"conditions": conditions, "order": [("ID", True)]}
        query = ""
        if "query" in self.get and self.get.getfirst("query", False):
            query = self.get.getfirst("query", "")
            linkarguments["query"] = query
            products_method = model.Product.Search
            products_args["query"] = query
        else:
            products_method = model.Product.List

        products = PagedResult(
            self.pagesize,
            self.get.getfirst("page", 1),
            products_method,
            self.connection,
            products_args,
        )

        return {
            "supplier": supplier,
            "products": products,
            "linkarguments": urllib.parse.urlencode(linkarguments) or "",
            "query": query,
            "suppliers": list(supplier_model.Supplier.List(self.connection)),
            "product_form": product_form,
        }

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.TemplateParser("product.html")
    def RequestProduct(self, sku, product_form=None, assemble_form=None):
        """Returns the product page"""
        product = model.Product.FromSku(self.connection, sku)
        parts = product.parts
        if "unlimitedstock" in self.get:
            stock = list(product.Stock(order=[("dateCreated", True)]))
            stockrows = False
        else:
            stock = list(
                product.Stock(
                    limit=int(self.pagesize),
                    order=[("dateCreated", True)],
                    yield_unlimited_total_first=True,
                )
            )
            stockrows = stock[0]
            stock = stock[1:]

        partsprice = {
            "partstotal": 0,
            "assembly": 0,
            "partcount": 0,
            "assembledtotal": 0,
        }
        for part in list(parts):
            partsprice["partcount"] += part["amount"]
            partsprice["assembly"] += part["assemblycosts"]
            partsprice["partstotal"] += part.subtotal
            partsprice["assembledtotal"] += part.subtotal + part["assemblycosts"]

        if not product_form:
            product_form = forms.ProductForm()
            product_form.process(data=product)
        return {
            "products": product.AssemblyOptions(),
            "possibleparts": model.Product.List(
                self.connection, conditions=[f'ID != {product["ID"]}']
            ),
            "parts": parts,
            "partsprice": partsprice,
            "product": product,
            "suppliers": supplier_model.Supplier.List(self.connection),
            "stock": stock,
            "stockrows": stockrows,
            "product_form": product_form,
            "assemble_form": assemble_form,
        }

    @loggedin
    @uweb3.decorators.checkxsrf
    def RequestProductNew(self):
        """Requests the creation of a new product."""
        form = forms.ProductForm(self.post)
        form.validate()
        if form.errors:
            return self.RequestProducts(product_form=form)

        try:
            product = model.Product.Create(self.connection, form.data)
        except common_model.InvalidNameError:
            return self.RequestInvalidcommand(
                error="Please enter a valid name for the product."
            )
        except self.connection.IntegrityError as error:
            uweb3.logging.error("Error: ", error)
            return self.Error("Something went wrong", 200)
        return self.req.Redirect(f"/product/{product['sku']}", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    def RequestProductSave(self, sku):
        """Saves changes to the product"""
        product = model.Product.FromSku(self.connection, sku)
        form = forms.ProductForm(self.post)
        form.validate()

        if form.errors:
            return self.RequestProduct(sku, product_form=form)

        product.update(form.data)
        try:
            product.Save()
        except self.connection.IntegrityError:
            return self.Error("That name was already taken.", 200)

        return uweb3.Redirect(f"/product/{product['sku']}", httpcode=303)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestProductAssemble(self, sku):
        """Add a new part to an existing product"""
        product = model.Product.FromSku(self.connection, sku)
        form = forms.ProductAssembleForm(self.post)
        form.validate()
        if form.errors:
            return self.RequestProduct(sku=sku, assemble_form=form)

        try:
            part = model.Product.FromSku(
                self.connection, self.post.getfirst("part")
            )  # TODO: get part SKU
            model.Productpart.Create(
                self.connection,
                {
                    "product": product,
                    "part": part,
                    "amount": int(self.post.getfirst("amount", 1)),
                    "assemblycosts": float(
                        self.post.getfirst("assemblycosts", part["assemblycosts"])
                    ),
                },
            )
        except ValueError:
            return self.RequestInvalidcommand(
                error="Input error, some fields are wrong."
            )
        except self.connection.IntegrityError:
            return self.Error("That part was already assembled in this product!", 200)
        return self.req.Redirect(f"/product/{product['sku']}", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestProductAssemblySave(self, sku):
        """Update a products assembly by adding, removing or updating part
        references"""
        product = model.Product.FromSku(self.connection, sku)
        deletes = self.post.getfirst("delete", [])
        updates = {
            "amount": self.post.getfirst("amount", []),
            "assemblycosts": self.post.getfirst("assemblycosts", []),
        }

        for mate in product.parts:
            mateid = str(mate["ID"])
            if mateid in deletes:
                mate.Delete()
            else:
                for key in mate:
                    if key in updates and mateid in updates[key]:
                        mate[key] = updates[key][mateid]
                mate.Save()
        return self.req.Redirect(f"/product/{product['sku']}", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestProductRemove(self, sku):
        """Removes the product"""
        product = model.Product.FromSku(self.connection, sku)
        product.Delete()
        return self.req.Redirect("/", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestProductStock(self, sku):
        """Creates a stock change for the product, either from a new shipment, or
        by assembling/ disassembling a product from its parts."""
        product = model.Product.FromSku(self.connection, sku)
        try:
            if "assemble" in self.post:
                product.Assemble(
                    int(self.post.getfirst("assemble", 1)),
                    self.post.getfirst("reference", None),
                    self.post.getfirst("lot", None),
                )
            elif "disassemble" in self.post:
                product.Disassemble(
                    int(self.post.getfirst("disassemble", 1)),
                    self.post.getfirst("reference", None),
                    self.post.getfirst("lot", None),
                )
            else:
                model.Stock.Create(
                    self.connection,
                    {
                        "product": product,
                        "amount": int(self.post.getfirst("amount", 1)),
                        "reference": self.post.getfirst("reference", ""),
                        "lot": self.post.getfirst("lot", ""),
                    },
                )
        except common_model.AssemblyError as error:
            return self.Error(error)
        return self.req.Redirect(f"/product/{product['sku']}", httpcode=301)

    @loggedin
    @uweb3.decorators.TemplateParser("gs1.html")
    def RequestGS1(self):
        """Returns the gs1 page"""
        products = PagedResult(
            self.pagesize,
            self.get.getfirst("page", 1),
            model.Product.List,
            self.connection,
            {"conditions": ["gs1 is not null"], "order": [("gs1", False)]},
        )
        return {"products": products}

    @loggedin
    @uweb3.decorators.TemplateParser("ean.html")
    def RequestEAN(self):
        """Returns the EAN page"""
        products = PagedResult(
            self.pagesize,
            self.get.getfirst("page", 1),
            model.Product.List,
            self.connection,
            {
                "conditions": ["(gs1 is not null or ean is not null)"],
                "order": [("ean", False)],
            },
        )
        return {"products": products}
