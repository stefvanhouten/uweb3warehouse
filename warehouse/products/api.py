#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

import uweb3

from warehouse import basepages
from warehouse.common import model as common_model
from warehouse.common.decorators import apiuser, json_error_wrapper
from warehouse.products import helpers, model


class PageMaker(basepages.PageMaker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_user = None
        self.apikey = None

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProducts(self):
        """Returns the product Json"""
        return {"products": list(model.Product.List(self.connection))}

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProduct(self, sku):
        """Returns the product Json"""
        product = model.Product.FromSku(self.connection, sku)
        return {
            "product": product,
            "currentstock": product.currentstock,
            "possiblestock": product.possiblestock["available"],
        }

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProductSearch(self, sku):
        """Returns the product Json"""
        product = model.Product.FromSku(self.connection, sku)
        return {
            "product": product["name"],
            "cost": product["cost"],
            "sku": product["sku"],
            "assemblycosts": product["assemblycosts"],
            "vat": product["vat"],
            "stock": product.currentstock,
            "possible_stock": product.possiblestock["available"],
        }

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProductStock(self, sku):
        """Updates the stock for a product, assembling if needed

        Send negative amount to Sell a product, positive amount to put product back
        into stock"""
        product = model.Product.FromSku(self.connection, sku)
        amount = int(self.post.get("amount", -1))
        currentstock = product.currentstock
        if (
            amount < 0 and abs(amount) > currentstock  # only assemble when we sell
        ):  # only assemble when we have not enough stock
            try:
                product.Assemble(
                    abs(amount)
                    - currentstock,  # only assemble what is missing for this sale
                    "Assembly for %s" % self.post.get("reference")
                    if "reference" in self.post
                    else None,
                )
            except common_model.AssemblyError as error:
                raise ValueError(error.args[0])

        # by now we should have enough products in stock, one way or another
        model.Stock.Create(
            self.connection,
            {
                "product": product,
                "amount": amount,
                "reference": self.post.get("reference", ""),
            },
        )
        model.Product.commit(self.connection)
        return {"stock": product.currentstock, "possible_stock": product.possiblestock}

    @uweb3.decorators.ContentType("application/json")
    @json_error_wrapper
    @apiuser
    def JsonProductStockBulk(self):
        products = self.post.get("products")
        model.Product.autocommit(self.connection, False)
        try:
            for product in products:
                helpers.update_stock(
                    self.connection,
                    product["name"],
                    product["quantity"],
                    self.post.get("reference", ""),
                )
        except Exception as ex:
            model.Product.rollback(self.connection)
            raise ex
        finally:
            model.Product.autocommit(self.connection, True)
        return {"products": products}
