from warehouse.products import api, products

urls = [
    (
        "/products",
        (products.PageMaker, "RequestProducts"),
    ),
    ("/gs1", (products.PageMaker, "RequestGS1")),
    ("/ean", (products.PageMaker, "RequestEAN")),
    (
        "/product/([^/]*)",
        (products.PageMaker, "RequestProductSave"),
        "POST",
    ),
    (
        "/product/([^/]*)",
        (products.PageMaker, "RequestProduct"),
        "GET",
    ),
    ("/", (products.PageMaker, "RequestProductNew"), "POST"),
    (
        "/product/([^/]*)/delete",
        (products.PageMaker, "RequestProductRemove"),
        "POST",
    ),
    (
        "/product/([^/]*)/assemble",
        (products.PageMaker, "RequestProductAssemble"),
        "POST",
    ),
    (
        "/product/([^/]*)/assembly",
        (products.PageMaker, "RequestProductAssemblySave"),
        "POST",
    ),
    (
        "/product/([^/]*)/stock/assemble",
        (products.PageMaker, "RequestProductStockAssemble"),
        "POST",
    ),
    (
        "/product/([^/]*)/stock/disassemble",
        (products.PageMaker, "RequestProductStockDisassemble"),
        "POST",
    ),
    (
        "/product/([^/]*)/stock/add",
        (products.PageMaker, "RequestProductStockAdd"),
        "POST",
    ),
    (
        "/product/([^/]*)/suppliers",
        (products.PageMaker, "RequestProductSuppliers"),
    ),
    (
        "/product/([^/]*)/suppliers/([0-9]+)/delete",
        (products.PageMaker, "RequestProductRemoveSupplier"),
        "POST",
    ),
    (
        "/product/([^/]*)/prices",
        (products.PageMaker, "RequestProductPrices"),
    ),
    (
        "/product/([^/]*)/prices/([0-9]+)/delete",
        (products.PageMaker, "RequestDeleteProductPrice"),
    ),
    (
        "/api/v1/product/([^/]*)",
        (api.PageMaker, "JsonProduct"),
        "GET",
    ),
    (
        "/api/v1/products",
        (api.PageMaker, "JsonProducts"),
        "GET",
    ),
    (
        "/api/v1/search_product/([^/]*)",
        (api.PageMaker, "JsonProductSearch"),
    ),
    (
        "/api/v1/product/([^/]*)/stock",
        (api.PageMaker, "JsonProductStock"),
        "POST",
    ),
    (
        "/api/v1/products/bulk_stock",
        (api.PageMaker, "JsonProductStockBulk"),
        "POST",
    ),
]
