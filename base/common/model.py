NOTDELETEDDATE = "1000-01-01 00:00:00"
NOTDELETED = 'dateDeleted = "%s"' % NOTDELETEDDATE


class InvalidNameError(Exception):
    """Invalid name value."""


class WarehouseException(Exception):
    """A general Catch all error for the warehouse software"""


class AssemblyError(WarehouseException):
    """The requested operation cannot continue because we could not assemble a
    product as requested."""
