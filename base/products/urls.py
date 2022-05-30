from base.products import products

urls = [
    (
        "/products",
        (products.PageMaker, "RequestProducts"),
    ),
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
        "/product/([^/]*)/remove",
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
        "/product/([^/]*)/stock",
        (products.PageMaker, "RequestProductStock"),
        "POST",
    ),
    (
        "/api/v1/product/([^/]*)",
        (products.PageMaker, "JsonProduct"),
        "GET",
    ),
    (
        "/api/v1/products",
        (products.PageMaker, "JsonProducts"),
        "GET",
    ),
    (
        "/api/v1/search_product/([^/]*)",
        (products.PageMaker, "JsonProductSearch"),
    ),
    (
        "/api/v1/product/([^/]*)/stock",
        (products.PageMaker, "JsonProductStock"),
        "POST",
    ),
    (
        "/api/v1/products/bulk_stock",
        (products.PageMaker, "JsonProductStockBulk"),
        "POST",
    ),
]
