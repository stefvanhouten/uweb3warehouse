#!/usr/bin/python3
"""Database abstraction model for the warehouse."""

__author__ = "Jan Klopper <janklopper@underdark.nl>"
__version__ = "1.0"

# standard modules
import datetime
import re

import pytz

# Custom modules
from uweb3 import model

from base.login import model as login_model


class Supplier(model.Record):
    """Provides a model abstraction for the Supplier table"""

    @classmethod
    def List(cls, connection, conditions=[], *args, **kwargs):
        """Returns the Suppliers filterd on not deleted"""
        return super().List(
            connection,
            conditions=[login_model.NOTDELETED] + conditions,
            *args,
            **kwargs
        )

    @classmethod
    def Search(cls, connection, query=None, conditions=None, **kwargs):
        """Returns the articles matching the search

        Arguments:
        @ connection: sqltalk.connection
          Database connection to use.
        % query: str
          Filters on name
        """
        if not conditions:
            conditions = []
        return cls.List(
            connection,
            conditions=['name like "%%%s%%"' % connection.EscapeValues(query)[1:-1]]
            + conditions,
            order=[("ID", True)],
            **kwargs
        )

    @classmethod
    def FromName(cls, connection, name, conditions=[]):
        """Returns the supplier of the given common name.

        Arguments:
          @ connection: sqltalk.connection
            Database connection to use.
          @ name: str
            The common name of the collection.

        Raises:
          NotExistError:
            The given supplier name does not exist.

        Returns:
          Supplier: supplier abstraction class.
        """
        safe_name = connection.EscapeValues(name)
        with connection as cursor:
            supplier = cursor.Select(
                table=cls.TableName(),
                conditions=["name=%s" % safe_name, login_model.NOTDELETED] + conditions,
            )
        if not supplier:
            raise cls.NotExistError("There is no supplier with common name %r" % name)
        return cls(connection, supplier[0])

    def Delete(self):
        """Overwrites the default Delete and sets the dateDeleted datetime instead"""
        self["dateDeleted"] = str(pytz.utc.localize(datetime.datetime.utcnow()))[0:19]
        self.Save()

    # def Products(self):
    #     """List products for this supplier"""
    #     return self.__children__(Products)

    def _PreCreate(self, cursor):
        super()._PreCreate(cursor)
        if self["gscode"]:
            self["gscode"] = self["gscode"][:10]
        if self["name"]:
            self["name"] = re.search(
                "([\w\-_\.,]+)", self["name"].replace(" ", "_")
            ).groups()[0][:45]
        if not self["name"]:
            raise login_model.InvalidNameError("Provide a valid name")

    def _PreSave(self, cursor):
        super()._PreSave(cursor)
        if self["gscode"]:
            self["gscode"] = self["gscode"][:10]
        if self["name"]:
            self["name"] = re.search(
                "([\w\-_\.,]+)", self["name"].replace(" ", "_")
            ).groups()[0][:45]
        if not self["name"]:
            raise login_model.InvalidNameError("Provide a valid name")
