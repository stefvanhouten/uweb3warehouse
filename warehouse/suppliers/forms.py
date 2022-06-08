import collections

from wtforms import FileField, Form, SelectField, StringField, validators

from warehouse.products.forms import SupplierProduct


class ImportSupplierStock(Form):
    column_name_mapping = StringField(
        "Product column name",
        [validators.DataRequired()],
        description="The column name in the file that contains the product name.",
    )
    column_stock_mapping = StringField(
        "Stock column name",
        [validators.DataRequired()],
        description="The column name in the file that contains the stock amount.",
    )
    fileupload = FileField("Select files")


class SupplierAddProductForm(SupplierProduct):
    """This is the form that is used when a supplier wants to add a product.

    The only difference with SupplierProduct is that it contains a list of all available products in the warehouse.
    """

    product = SelectField("product")

    field_order = ["product"]

    def __iter__(self):
        """Allows setting the order for fields.

        this is needed because inheriting from a super class will mess with the ordering.
        """
        ordered_fields = collections.OrderedDict()

        for name in getattr(self, "field_order", []):
            ordered_fields[name] = self._fields.pop(name)

        ordered_fields.update(self._fields)

        self._fields = ordered_fields
        return super().__iter__()
