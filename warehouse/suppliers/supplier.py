import os
from io import StringIO

import uweb3

from warehouse import basepages
from warehouse.common import model as common_model
from warehouse.common.decorators import NotExistsErrorCatcher, loggedin
from warehouse.common.helpers import PagedResult
from warehouse.products import helpers
from warehouse.products import model as product_model
from warehouse.suppliers import forms, model


class PageMaker(basepages.PageMaker):
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

    @loggedin
    @uweb3.decorators.TemplateParser("suppliers.html")
    def RequestSuppliers(self, error=None, success=None):
        """Returns the suppliers page"""
        suppliers = None
        query = ""
        if "query" in self.get and self.get.getfirst("query", False):
            suppliermethod = model.Supplier.Search
            supplierarguments = {
                "query": self.get.getfirst("query", ""),
                "order": [("ID", True)],
            }
        else:
            suppliermethod = model.Supplier.List
            supplierarguments = {"order": [("ID", True)]}

        suppliers = PagedResult(
            self.pagesize,
            self.get.getfirst("page", 1),
            suppliermethod,
            self.connection,
            supplierarguments,
        )
        return {
            "suppliers": suppliers,
            "query": query,
            "error": error,
            "success": success,
        }

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestSupplierSave(self, name):
        """Returns the supplier page"""
        supplier = model.Supplier.FromName(self.connection, name)
        for key in (
            "name",
            "website",
            "telephone",
            "contact_person",
            "email_address",
            "gscode",
        ):
            supplier[key] = self.post.getfirst(key, None)
        supplier.Save()
        return self.RequestSuppliers(success="Changes saved.")

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.TemplateParser("supplier.html")
    def RequestSupplier(self, name):
        """Returns the supplier page"""
        supplier_stock_form = forms.ImportSupplierStock(self.post)

        return dict(
            supplier=model.Supplier.FromName(self.connection, name),
            supplier_stock_form=supplier_stock_form,
        )

    @loggedin
    @uweb3.decorators.checkxsrf
    def RequestSupplierNew(self):
        """Requests the creation of a new supplier."""
        try:
            supplier = model.Supplier.Create(
                self.connection,
                {
                    "name": self.post.getfirst("name", "").replace(" ", "_"),
                    "website": self.post.getfirst("website")
                    if "website" in self.post
                    else None,
                    "telephone": self.post.getfirst("telephone")
                    if "telephone" in self.post
                    else None,
                    "contact_person": self.post.getfirst("contact_person")
                    if "contact_person" in self.post
                    else None,
                    "email_address": self.post.getfirst("email_address")
                    if "email_address" in self.post
                    else None,
                    "gscode": self.post.getfirst("gscode")
                    if "gscode" in self.post
                    else None,
                },
            )
        except ValueError:
            return self.RequestInvalidcommand(
                error="Input error, some fields are wrong."
            )
        except common_model.InvalidNameError:
            return self.RequestInvalidcommand(
                error="Please enter a valid name for the supplier."
            )
        except self.connection.IntegrityError:
            return self.Error("That name was already taken, go back, try again!", 200)
        return self.req.Redirect("/supplier/%s" % supplier["name"], httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    def RequestSupplierRemove(self, supplier):
        """Removes the supplier"""
        supplier = model.Supplier.FromName(self.connection, supplier)
        supplier.Delete()
        return self.req.Redirect("/suppliers", httpcode=301)

    @loggedin
    @NotExistsErrorCatcher
    @uweb3.decorators.checkxsrf
    @uweb3.decorators.TemplateParser("supplier.html")
    def UpdateSupplierStock(self, supplier):
        supplier_stock_form = forms.ImportSupplierStock(self.post)
        if not self.files or not self.files.get("fileupload"):
            return self.Error(error="No file was uploaded.")

        column_name_mapping = self.post.getfirst("column_name_mapping", None)
        column_stock_mapping = self.post.getfirst("column_stock_mapping", None)

        if not column_name_mapping or not column_stock_mapping:
            return self.Error(error="Name and stock mapping values must be set.")

        supplier = model.Supplier.FromName(self.connection, supplier)

        file = self.files["fileupload"][0]

        parser = helpers.StockParser(
            file_path=StringIO(file["content"]),
            columns=(
                column_name_mapping,
                column_stock_mapping,
            ),
            normalize_columns=(column_name_mapping,),
        )

        try:
            parsed_result = parser.Parse()
        except KeyError as exception:
            return self.RequestInvalidcommand(error=exception.args[0])

        products = list(
            product_model.Product.List(
                self.connection, conditions=[f'supplier = {supplier["ID"]}']
            )
        )

        importer = helpers.StockImporter(
            self.connection,
            {
                "amount": column_stock_mapping,
                "name": column_name_mapping,
            },
        )
        importer.Import(
            parsed_result,
            products,
        )
        return {
            "supplier": supplier,
            "processed_products": importer.processed_products,
            "unprocessed_products": importer.unprocessed_products,
            "supplier_stock_form": supplier_stock_form,
        }
