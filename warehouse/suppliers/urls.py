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
        "/supplier/([^/]*)/remove",
        (supplier.PageMaker, "RequestSupplierRemove"),
        "POST",
    ),
]
