import collections

from wtforms import EmailField, FileField, Form, SelectField, StringField, validators

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


class SupplierForm(Form):
    name = StringField(
        "Name",
        [validators.DataRequired(), validators.Length(max=45)],
        description="The name of the supplier.",
    )
    website = StringField(
        "Website",
        [validators.Optional(), validators.Length(min=10, max=255)],
        description="The website of the supplier.",
    )
    telephone = StringField(
        "Telephone",
        [validators.DataRequired(), validators.Length(min=5, max=45)],
        description="The telephone of the supplier.",
    )
    contact_person = StringField(
        "Contact person",
        [validators.Optional(), validators.Length(max=255)],
        description="The name of the contact person at the supplier.",
    )
    email_address = EmailField(
        "Email address",
        [validators.DataRequired(), validators.Email()],
        description="The email address of the supplier.",
    )
    gscode = StringField(
        "GSCode",
        [validators.Optional()],
        description="The GSCode of the supplier.",
    )
