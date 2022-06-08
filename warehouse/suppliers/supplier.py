import os
from io import StringIO

import uweb3

from warehouse import basepages
from warehouse.common import model as common_model
from warehouse.common.decorators import NotExistsErrorCatcher, loggedin
from warehouse.common.helpers import PagedResult
from warehouse.products import helpers as product_helpers
from warehouse.suppliers import forms, helpers, model


class PageMaker(basepages.PageMaker):
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

    @loggedin
    @NotExistsErrorCatcher
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
    @uweb3.decorators.TemplateParser("supplier_products.html")
    def RequestSupplierProducts(self, supplierID):
        supplier = model.Supplier.FromPrimary(self.connection, supplierID)
        supplier_products = list(
            model.Supplierproduct.Products(self.connection, supplier)
        )
        return dict(
            supplier_products=supplier_products,
            supplier=supplier,
        )

    @loggedin
    @NotExistsErrorCatcher
    def RequestSupplierProductDelete(self, supplierID, productID):
        supplier = model.Supplier.FromPrimary(self.connection, supplierID)
        product = model.Supplierproduct.FromPrimary(self.connection, productID)
        if product["supplier"] != supplier:
            return
        product.Delete()
        return self.req.Redirect(f"/supplier/{supplierID}/products")

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
    def RequestSupplier(self, name, supplier_stock_form=None):
        """Returns the supplier page"""
        if not supplier_stock_form:
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
        supplier = model.Supplier.FromName(self.connection, supplier)

        if not self.files or not self.files.get("fileupload"):
            return self.Error(error="No file was uploaded.")

        supplier_stock_form = forms.ImportSupplierStock(self.post)
        supplier_stock_form.fileupload.data = self.files.get("fileupload")
        supplier_stock_form.validate()

        if supplier_stock_form.errors:
            return self.RequestSupplier(
                name=supplier, supplier_stock_form=supplier_stock_form
            )

        try:
            processed_products, unprocessed_products = helpers.import_stock_from_file(
                supplier_stock_form, supplier, self.connection
            )
        except KeyError as exception:
            return self.RequestInvalidcommand(error=exception.args[0])

        return {
            "supplier": supplier,
            "processed_products": processed_products,
            "unprocessed_products": unprocessed_products,
            "supplier_stock_form": supplier_stock_form,
        }
