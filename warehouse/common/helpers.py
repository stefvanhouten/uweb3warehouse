#!/usr/bin/python3
"""Helper functions"""
__author__ = "Jan Klopper (jan@underdark.nl)"
__version__ = 0.1

import decimal
import math


def round_price(d):
    if not isinstance(d, decimal.Decimal):
        d = decimal.Decimal(d)
    cents = decimal.Decimal("0.01")
    return d.quantize(cents, decimal.ROUND_HALF_UP)


class SortTable:
    def __init__(
        self,
        modelCall,
        connection=None,
        modelargs=None,
        columns=None,
        sort=None,
        linkbase=None,
        linkarguments=None,
    ):

        if (
            connection and type(modelCall.__self__) is type
        ):  # is this in unbound method?, ifso it needs a connection argument
            self.items = modelCall(connection, **modelargs)
        else:  # is a bound method of a model object that already has a connection reference
            self.items = modelCall(**modelargs)

        self.linkbase = linkbase or ""
        self.linkarguments = linkarguments or ""

    def __iter__(self):
        return iter(self.items)


class PagedResult:
    def __init__(
        self,
        pagesize,
        page,
        modelCall,
        connection=None,
        modelargs=None,
        maxlinks=10,
    ):
        """Returns a dictionary with pagination information based on parameters.

         Takes:
           pagesize: Number specifying the amount of items per page, int
           page: The current page number, int
           modelCall: Function object for calling the model, function
           connection: An optional database connection object, object
           modelargs: An optional model call argument dictionary, dict

        Creates the following members:
           pagesize: The pagesize variable given as a parameter, int
           offset: The offset based on the pagesize, int
           totalcount: The total item count for the unpaginated query, int
           pagecount: The total page count, int
           last: The last page number, int
           next:  The next page number, int
           prev: The previous page number, int
           current: The current page number, int
        """
        modelargs = {} if modelargs is None else modelargs
        self.pagesize = int(pagesize)
        try:
            self.current = int(page)
        except Exception:
            self.current = 0

        self.offset = modelargs["offset"] = self.pagesize * (self.current - 1)
        modelargs["yield_unlimited_total_first"] = True
        modelargs["limit"] = self.pagesize
        if (
            connection and type(modelCall.__self__) is type
        ):  # is this in unbound method?, ifso it needs a connection argument
            items = list(modelCall(connection, **modelargs))
        else:  # is a bound method of a model object that already has a connection reference
            items = list(modelCall(**modelargs))
        self.totalcount = itemcount = items[0]
        self.items = items[1:]
        self.last = self.pagecount = int(math.ceil(float(itemcount) / self.pagesize))

        if self.pagecount < maxlinks:
            self.pagenumbers = range(1, self.pagecount + 1)
        else:
            self.pagenumbers = [
                *range(max(1, self.current - int(maxlinks / 2)), self.current),
                self.current,
                *range(
                    self.current + 1,
                    min(
                        self.current + int(maxlinks / 2) + 1,
                        self.pagecount + 1,
                    ),
                ),
            ]
        self.next = self.current + 1 if self.current + 1 <= self.pagecount else None
        self.prev = self.current - 1 if self.current > 1 else None

    def __iter__(self):
        return iter(self.items)


class BaseFactory:
    """Base class for factory classes."""

    def __init__(self):
        self._registered_items = {}

    def register(self, key, builder):
        """Registers a service within the factory.

        Args:
            key (str): The name of the service.
            builder: The builder class for the given service.
                    The builder class is used to supply the Service class with the correct
                    attributes on call. The builder class must have a __call__ method
                    that supplies the service with the provided arguments.
        """
        self._registered_items[key] = builder

    def get_registered_item(self, key, **kwargs):
        """Retrieve a service by name.

        Args:
            key (str): The name of the service by which it was registered.

        Raises:
            ValueError: Raised when the service could not be found in the registered services.

        Returns:
            _type_: An authentication service.
        """
        builder = self._registered_items.get(key)
        if not builder:
            raise ValueError(f"No item with key {key} is registered.")
        return builder(**kwargs)
