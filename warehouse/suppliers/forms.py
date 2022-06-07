from wtforms import FileField, Form, StringField, validators


class ImportSupplierStock(Form):
    column_name_mapping = StringField(
        "Product column name",
        [validators.DataRequired()],
        description="The column name in the file that contains the product name.",
    )
    column_stock_mapping = StringField(
        "Stock column name",
        [validators.Length(min=5, max=255), validators.DataRequired()],
        description="The column name in the file that contains the stock amount.",
    )
    fileupload = FileField("Select files")
