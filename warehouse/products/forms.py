import decimal
from collections import namedtuple

from wtforms import (
    DecimalField,
    Form,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
    ValidationError,
    validators,
)


class ProductForm(Form):
    sku = StringField(
        "sku",
        [validators.Length(min=1, max=45), validators.InputRequired()],
        description="""The name for each sku in your warehouse must be unique,
                      only products that can be ordered by end customers should have an easily recognizable sku.""",
    )
    name = StringField(
        "name",
        [validators.Length(min=5, max=255), validators.DataRequired()],
        description="The name of the product",
    )
    ean = StringField(
        "ean",
        [validators.Length(min=1, max=13), validators.Optional()],
        description="The ean barcode for each product or part in your warehouse must be unique.",
    )
    gs1 = IntegerField(
        "gs1",
        [validators.NumberRange(min=1, max=32767), validators.Optional()],
        description="The gs1 for each product or part in your warehouse must be unique.",
    )
    description = TextAreaField("description", validators=[validators.Optional()])
    assemblycosts = DecimalField(
        "assemblycosts",
        rounding=decimal.ROUND_UP,
        places=2,
        validators=[validators.InputRequired(), validators.NumberRange(min=0)],
        description="What does it cost to use this part in a bifer product? A sticker needs to be applied, a jar needs to be filled.",
    )


class SupplierProduct(Form):
    """Form used to add a supplier to a product on the product page."""

    supplier = SelectField("supplier")
    cost = DecimalField(
        "cost",
        rounding=decimal.ROUND_UP,
        places=2,
        description="The amount that we pay for the product.",
        validators=[validators.InputRequired(), validators.NumberRange(min=0)],
    )
    vat = DecimalField(
        "vat",
        rounding=decimal.ROUND_UP,
        places=2,
        description="The VAT percentage that we pay for the product.",
        validators=[
            validators.InputRequired(),
            validators.NumberRange(min=0, max=100),
        ],
    )
    name = StringField(
        "name",
        [validators.Length(min=5, max=255), validators.DataRequired()],
        description="The name that the supplier has for the product",
    )
    lead = IntegerField(
        "lead",
        [validators.NumberRange(min=0), validators.Optional()],
        description="The amount of days that it takes to ship the product from the supplier to us.",
    )
    supplier_sku = StringField(
        "sku",
        [validators.Optional(), validators.Length(max=45)],
        description="The sku that the supplier uses for this product",
    )
    supplier_stock = IntegerField(
        "supplier_stock",
        [validators.NumberRange(min=0), validators.Optional()],
        description="The amount of stock that the supplier currently has for this product.",
    )


class ProductAssembleFromPartForm(Form):
    part = SelectField("part")
    amount = IntegerField(
        "amount",
        [validators.NumberRange(min=1, max=65535)],
        description="How many of the selected product are used as parts in the current product?",
    )
    assemblycosts = DecimalField(
        "assemblycosts",
        rounding=decimal.ROUND_UP,
        places=2,
        validators=[validators.InputRequired(), validators.NumberRange(min=0)],
        description="What does it cost to use the selected product as a part in the current product? A sticker needs to be applied, a jar needs to be filled.",
    )


class ProductAssemblyForm(Form):
    amount = IntegerField("amount")
    reference = StringField(
        "reference",
        [validators.Optional(), validators.Length(max=255)],
        description="The invoice ID to the customer.",
    )
    lot = StringField(
        "lot",
        [validators.Optional(), validators.Length(max=45)],
        description="The Lot number of this shipment.",
    )


class ProductStockForm(ProductAssemblyForm):
    piece_price = DecimalField(
        "piece price",
        rounding=decimal.ROUND_UP,
        places=2,
        description="How much did you pay for each individual piece from the supplier?.",
    )

    def validate_piece_price(self, field):
        if self.amount is not None:
            if self.amount.data >= 0 and field.data is None:
                raise ValidationError(
                    "If you are adding stock, you must also specify a piece price."
                )


class ProductPriceForm(Form):
    price = DecimalField(
        "price",
        rounding=decimal.ROUND_UP,
        places=2,
        validators=[validators.InputRequired(), validators.NumberRange(min=0)],
        description="The sale price for the product",
    )
    start_range = IntegerField(
        "start_range",
        [validators.NumberRange(min=1)],
        description="The amount of products that need to be purchased before the price starts to apply.",
    )


class ProductVatForm(Form):
    vat = DecimalField(
        "vat",
        rounding=decimal.ROUND_UP,
        places=2,
        validators=[
            validators.InputRequired(),
            validators.NumberRange(min=0, max=100),
        ],
        description="The vat percentage for this product",
    )


class StockMutationFactory:
    def __init__(self):
        self._forms = {}

    def register_form(self, name, form):
        self._forms[name] = form

    def get_form(self, name):
        form = self._forms.get(name)
        if not form:
            raise ValueError(
                f"Form {name} could not be found because it was not registered."
            )
        return form


def get_stock_factory(postdata=None):
    """Factory used to create forms that are similar to the stock mutation form but have different descriptions.

    Args:
        postdata (dict, optional): The PageMaker.post data from the request. Defaults to None.

    Returns:
        wtfforms.Form: The form used for the stock mutation.
    """
    factory = StockMutationFactory()
    _register_default_forms(factory, postdata)
    return factory


def _register_default_forms(factory, postdata):
    """Register some forms that have the same structure but different descriptions.
    This mutates the factory object.
    """
    form_tuple = namedtuple("form_tuple", "prefix amount reference lot form_name")
    lot = "The lot number for these newly assembled products"
    default_forms = [
        form_tuple(
            prefix="product-assembly",
            amount="How many were assembled",
            reference="Optional reference for this assembly",
            lot=lot,
            form_name="assemble_from_part",
        ),
        form_tuple(
            prefix="product-disassembly",
            amount="How many were disassembled",
            reference="The invoice ID from the supplier, or the customer",
            lot=lot,
            form_name="disassemble_into_parts",
        ),
    ]
    for item in default_forms:
        form = ProductAssemblyForm(postdata, prefix=item.prefix)
        form.amount.description = item.amount
        form.reference.description = item.reference
        form.lot.description = item.lot
        factory.register_form(item.form_name, form)

    factory.register_form(
        "stock_form", ProductStockForm(postdata, prefix="product-stock")
    )
