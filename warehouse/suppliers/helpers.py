from io import StringIO

from warehouse.products import helpers as product_helpers
from warehouse.suppliers import model


def import_stock_from_file(supplier_stock_form, supplier, connection):
    """Attempts to import the stock from the file that was uploaded.

    Args:
        supplier_stock_form (forms.ImportSupplierStock): The form used to upload the file and specify the column names
        supplier (model.Supplier): The supplier object
        connection (PageMaker.connection): Connection object to access the database

    Returns:
        (list(Product), list(ProductPair)): List containing the processed Products and
            a list containing the ProductPairs of unprocessed products.

    Raises:
        KeyError: If the column names are not found in the file.
    """
    parsed_data = _parse_file(supplier_stock_form)
    products = get_supplier_products(connection, supplier)
    importer = _setup_importer(connection, supplier_stock_form, supplier)
    return importer.Import(
        parsed_data,
        products,
    )


def _parse_file(supplier_stock_form):
    file = supplier_stock_form.fileupload.data[0]
    parser = product_helpers.StockParser(
        file_path=StringIO(file["content"]),
        columns=(
            supplier_stock_form.column_name_mapping.data,
            supplier_stock_form.column_stock_mapping.data,
        ),
        normalize_columns=(supplier_stock_form.column_name_mapping.data,),
    )

    return parser.Parse()


def get_supplier_products(connection, supplier):
    """Return the SupplierProducts for the supplier.

    Args:
        connection (PageMaker.connection):  Connection object to access the database
        supplier (model.Supplier): The supplier object from which we want to retrieve the SupplierProducts.

    Returns:
        Generator: A generator that yields the SupplierProducts for the supplier.
    """
    return model.Supplierproduct.List(
        connection, conditions=[f'supplier = {supplier["ID"]}']
    )


def _setup_importer(connection, supplier_stock_form, supplier):
    return product_helpers.StockImporter(
        connection,
        {
            "name": supplier_stock_form.column_name_mapping.data,
            "amount": supplier_stock_form.column_stock_mapping.data,
        },
        supplier,
    )
