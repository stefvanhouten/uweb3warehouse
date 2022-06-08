from warehouse.suppliers import supplier

urls = [
    (
        "/suppliers",
        (supplier.PageMaker, "RequestSupplierNew"),
        "POST",
    ),
    (
        "/supplier/updatestock/([^/]*)",
        (supplier.PageMaker, "UpdateSupplierStock"),
        "POST",
    ),
    (
        "/suppliers",
        (supplier.PageMaker, "RequestSuppliers"),
    ),
    (
        "/supplier/([^/]*)",
        (supplier.PageMaker, "RequestSupplierSave"),
        "POST",
    ),
    (
        "/supplier/([^/]*)",
        (supplier.PageMaker, "RequestSupplier"),
        "GET",
    ),
    (
        "/supplier/([^/]*)/products",
        (supplier.PageMaker, "RequestSupplierProducts"),
        "GET",
    ),
    (
        "/supplier/([^/]*)/products/([0-9]+)/delete",
        (supplier.PageMaker, "RequestSupplierProductDelete"),
        "POST",
    ),
    (
        "/supplier/([^/]*)/delete",
        (supplier.PageMaker, "RequestSupplierRemove"),
        "POST",
    ),
]
