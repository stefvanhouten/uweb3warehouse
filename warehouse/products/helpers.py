import difflib
from collections import namedtuple

import pandas

from warehouse.products import model


class StockParser:
    def __init__(self, file_path, columns, normalize_columns):
        """Attempts to find the columns and values from a passed html file object.

        Args:
            file_path (StringIO): The StringIO object containing the HTML with the table.
            columns (tuple[str]): The columns that we are interested in
            normalize_columns (_type_): The column containing the product name that should be normalized to match the database value.
        """
        self.columns = columns
        self.normalize_columns = normalize_columns
        self.file_path = file_path

    def Parse(self):
        """Start the parsing process."""
        dataframes = self._parse()
        return self._process_dataframes(dataframes)

    def _parse(self):
        """Read the file and attempt to find the columns."""
        return pandas.read_html(self.file_path, header=0)

    def _process_dataframes(self, dataframes):
        """Process the list of dataframes containing table elements.

        Args:
            dataframes (list[DataFrame]): List with dataframes found by pandas.read_html

        Returns:
            list[dict]: Returns the list with the matches.
        """
        processed = []
        # Because multiple tables can be present in a page we can have multiple dataframes.
        for dataframe in dataframes:
            processed.append(self._process_dataframe(dataframe.to_dict("record")))
        return processed

    def _process_dataframe(self, dataframe):
        """Mutate the dataframe by normalizing the columns that we are interested in so that the value matches the value stored in the database."""
        for result in dataframe:
            missing_columns = [
                column for column in self.columns if column not in result
            ]
            if missing_columns:
                raise KeyError(
                    f"The following columns could not be found: {missing_columns}"
                )
            self._normalize(result)
        return dataframe

    def _normalize(self, match):
        """Normalize only the columns which are of interest. This should be the column containing the product name."""
        for column in self.normalize_columns:
            match[column] = match[column].replace("/", "_")


class StockImporter:
    def __init__(self, connection, mapping):
        """Initialize the importer that will import the stock from the passed results.

        Args:
            connection (self.connection): Uweb3 connection object
            mapping (dict): Contains the key value mappings for the columns in the table.
                For example {"amount": "Op voorraad"} would mean that the amount column in the table is named "Op voorraad".
        """
        self._processed_products = []
        self._unprocessed_products = []
        self.connection = connection
        self.mapping = mapping

    def Import(self, parsed_results, products):
        """Attempt to find a database product for each result.
        If a product is found, add the stock to the product.

        Args:
            parsed_results (list[dict]): List of dictionaries that were normalized by the StockParser class
            products (list[model.Prouct]): A list of all the products from the supplier that we want to import
        """
        self.parsed_results = parsed_results
        self.products = products
        self.product_names = [p["name"] for p in self.products]
        for found_product_list in self.parsed_results:
            self._import_products(found_product_list)
        return self._processed_products, self._unprocessed_products

    def _import_products(self, products):
        for product in products:
            self._import_product(product)

    def _import_product(self, parsed_product):
        # Find corresponding product by mapping the column name to the database field name.
        # This is because every supplier can have a different naming convention.
        name = parsed_product[self.mapping["name"]]
        product = self._find_product(name)

        if not product:
            self._unprocessed_products.append(self._normalize_keys(parsed_product))
            return

        self._add_stock(product, parsed_product[self.mapping["amount"]])
        self._add_to_processed(parsed_product, product)

    def _find_product(self, name):
        """Attempt to find the closest matching database product for the passed name.

        Args:
            name (str): The name of the product that we want to find.

        Returns:
            product (model.Product): The product that was found to be the best match.
        """
        # Finds the top3 matches for the product name.
        closest_matches = difflib.get_close_matches(
            name, self.product_names, n=3, cutoff=0.8
        )
        # If no match is found return None
        if not closest_matches:
            return None
        # Get the actual Product object from the list of products and return it.
        return next((x for x in self.products if x["name"] == closest_matches[0]), None)

    def _add_to_processed(self, parsed_product, product):
        """Adds the parsed_product from the parsed file and the database product to a tuple
        and adds it to the processed_products list. The keys from the parsed_products are
        normalized before adding them to the list, this allows us to display parsed_products
        from different suppliers with the same key names.

        Args:
            parsed_product (_type_): The product that was found by the parser.
            product (model.Product): The product that was found in the database.
        """
        pair = namedtuple("ProductPair", "parsed_product product".split())
        normalized_result = self._normalize_keys(parsed_product)
        self._processed_products.append(pair(normalized_result, product))

    def _normalize_keys(self, result):
        """Normalize the keys of the result dictionary so that they match the database field names."""
        return {key: result[self.mapping[key]] for key in self.mapping.keys()}

    def _add_stock(self, product, amount):
        """Update the stock of the product with the amount that was found in the parsed file.

        Args:
            product (model.Product): The product that was found in the database.
            amount (int): The amount that was found in the parsed file (this is the current stock of the supplier)

        Returns:
            model.Stock: The added Stock record.
        """
        return model.Stock.Create(
            self.connection,
            {
                "product": product.key,
                "amount": amount,
            },
        )


def update_stock(connection, sku, amount, reference=None):
    product = model.Product.FromSku(connection, sku)
    currentstock = product.currentstock
    if (
        amount < 0 and abs(amount) > currentstock  # only assemble when we sell
    ):  # only assemble when we have not enough stock
        try:
            product.Assemble(
                abs(amount)
                - currentstock,  # only assemble what is missing for this sale
                "Assembly for %s" % reference,
            )
        except model.AssemblyError as error:
            raise ValueError(error.args[0])

    model.Stock.Create(
        connection,
        {
            "product": product,
            "amount": amount,
            "reference": reference,
        },
    )
    return {"stock": product.currentstock, "possible_stock": product.possiblestock}


def possibleparts_select_list(possibleparts):
    return [(p["sku"], f"{p['sku']} - {p['name']}") for p in possibleparts]


def suppliers_select_list(suppliers):
    return [(s["ID"], s["name"]) for s in suppliers]
