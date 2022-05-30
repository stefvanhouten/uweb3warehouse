#!/usr/bin/python
"""Request handlers for the uWeb3 warehouse inventory software"""

import locale

# standard modules
import time

# uweb modules
import uweb3
from uweb3.libs import mail

from base.common import model as common_model
from base.login import model as login_model

# project modules
from base.products import model as product_model

from .common.helpers import PagedResult


def CentRound(monies):
    """Rounds the given float to two decimals."""
    if monies:
        return "%.2f" % monies


class PageMaker(
    uweb3.DebuggingPageMaker,
    uweb3.LoginMixin,
    # products.PageMaker, supplier.PageMaker
):
    """Holds all the request handlers for the application"""

    DEFAULTPAGESIZE = 10

    def _PostInit(self):
        """Sets up all the default vars"""
        self.parser.RegisterTag("scripts", None)
        self.parser.RegisterTag("year", time.strftime("%Y"))
        self.parser.RegisterFunction("CentRound", CentRound)
        self.parser.RegisterFunction("ToID", lambda x: x.replace(" ", ""))
        self.parser.RegisterFunction("NullString", lambda x: "" if x is None else x)
        self.parser.RegisterFunction("DateOnly", lambda x: str(x)[0:10])
        self.parser.RegisterFunction(
            "TextareaRowCount", lambda x: len(str(x).split("\n"))
        )
        self.parser.RegisterTag(
            "header", self.parser.JITTag(lambda: self.parser.Parse("parts/header.html"))
        )
        self.parser.RegisterTag(
            "footer",
            self.parser.JITTag(
                lambda *args, **kwargs: self.parser.Parse(
                    "parts/footer.html", *args, **kwargs
                )
            ),
        )
        self.validatexsrf()
        self.parser.RegisterTag("xsrf", self._Get_XSRF())
        self.parser.RegisterTag("user", self.user)
        if self.options.get("general"):
            self.pagesize = int(
                self.options["general"].get("pagesize", self.DEFAULTPAGESIZE)
            )

    def _PreRequest(self):
        list(
            login_model.User.List(self.connection)
        )  # XXX: mysql connection bugged. Remove this
        if self.config.Read():
            try:
                locale.setlocale(
                    locale.LC_ALL, self.options["general"].get("locale", "en_GB")
                )
                self.parser.RegisterFunction(
                    "currency",
                    lambda x: locale.currency(x, symbol=False, grouping=True),
                )
            except (locale.Error, KeyError):
                self.parser.RegisterFunction("currency", lambda x: x)

    def _PostRequest(self, response):
        response.headers.update(
            {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
        return response

    def _ReadSession(self):
        """Attempts to read the session for this user from his session cookie"""
        try:
            user = login_model.Session(self.connection)
        except Exception:
            raise ValueError("Session cookie invalid")
        try:
            user = login_model.User.FromPrimary(self.connection, int(str(user)))
        except uweb3.model.NotExistError:
            return None
        if user["active"] != "true":
            raise ValueError("User not active, session invalid")
        return user

    @uweb3.decorators.TemplateParser("login.html")
    def RequestLogin(self, url=None):
        """Please login"""
        if self.user:
            return uweb3.Redirect("/products")
        if not url and "url" in self.get:
            url = self.get.getfirst("url")
        return {"url": url}

    @uweb3.decorators.loggedin
    @uweb3.decorators.checkxsrf
    @uweb3.decorators.TemplateParser("admin.html")
    def RequestAdmin(self):
        """Returns the admin page."""
        if self.user["ID"] != 1:
            return self.req.Redirect("/")

        currentusers = list(login_model.User.List(self.connection))
        if self.post:
            values = {}
            for key in (
                "useremail",
                "useractive",
                "userpassword",
                "userpassword_confirm",
                "userdelete",
            ):
                values[key] = self.post.getfirst(key, {})

        users = []
        for user in currentusers:
            # user changes
            userid = str(user["ID"])

            # we are posting the edit form, not the new form
            if "useremail" in self.post and "new" not in values["useremail"]:
                if userid in values["userdelete"]:
                    if user["ID"] != 1 or user["ID"] == self.user["ID"]:
                        user.Delete()
                else:
                    if userid in values["useremail"]:
                        user["email"] = values["useremail"][userid].strip()
                    if user["ID"] != 1 and user["ID"] != self.user["ID"]:
                        user["active"] = (
                            "true" if userid in values["useractive"] else "false"
                        )
                    else:
                        user["active"] = "true"
                    # handle password change
                    if (
                        userid in values["userpassword"]
                        and userid in values["userpassword_confirm"]
                        and len(values["userpassword"][userid].strip()) > 7
                    ):
                        if (
                            values["userpassword"][userid].strip()
                            != values["userpassword_confirm"][userid].strip()
                        ):
                            return {
                                "usererror": "Passwords do not match.",
                                "users": currentusers,
                            }
                        try:
                            user.UpdatePassword(values["userpassword"][userid].strip())
                        except ValueError:
                            return {
                                "usererror": "Password too short, 8 characters minimal.",
                                "users": currentusers,
                            }
                    user.Save()
                    users.append(user)
            else:
                users.append(user)

        # handle User creation
        if "useremail" in self.post and "new" in values["useremail"]:
            try:
                newuser = login_model.User.Create(
                    self.connection,
                    {
                        "email": values["useremail"].get("new", "").strip(),
                        "active": values["useractive"].get("new", "true"),
                        "password": "",
                    },
                )
                try:
                    newpassword = values["userpassword"].get("new", "").strip()
                    newuser.UpdatePassword(newpassword)
                except ValueError:
                    return {
                        "usererror": "Password too short, 8 characters minimal.",
                        "users": users,
                    }
                users.append(newuser)
            except common_model.InvalidNameError:
                return {
                    "usererror": "Provide a valid email address for the new user.",
                    "users": users,
                }
            except self.connection.IntegrityError:
                return {
                    "usererror": "That email address was already used for another user.",
                    "users": users,
                }
            else:
                content = self.parser.Parse(
                    "email/newuser.txt",
                    email=newuser["email"],
                    host=self.options["general"]["host"],
                    password=newpassword,
                )
                try:
                    with mail.MailSender(
                        local_hostname=self.options["general"]["host"]
                    ) as send_mail:
                        send_mail.Text(newuser["email"], "Warehouse account", content)
                except mail.SMTPConnectError:
                    if not self.debug:
                        return self.Error(
                            "Mail could not be send due to server error, please contact support."
                        )
            return {"usersucces": "Your new user was added", "users": users}
        return {"users": users}

    @uweb3.decorators.loggedin
    @uweb3.decorators.checkxsrf
    @uweb3.decorators.TemplateParser("usersettings.html")
    def RequestUserSettings(self):
        """Returns the user settings page."""
        # handle password change
        if "password" in self.post or "password_confirm" in self.post:
            password = self.post.getfirst("password", "")
            password_confirm = self.post.getfirst("password_confirm", "")
            if password != password_confirm:
                return {"error": "Passwords do not match, try again."}
            try:
                self.user.UpdatePassword(password)
            except ValueError:
                return {"error": "Passwords too short."}
            else:
                content = self.parser.Parse(
                    "email/updateuser.txt", email=self.user["email"]
                )
                try:
                    with mail.MailSender(
                        local_hostname=self.options["general"]["host"]
                    ) as send_mail:
                        send_mail.Text(
                            self.user["email"], "Warehouse account change", content
                        )
                except mail.SMTPConnectError:
                    if not self.debug:
                        return self.Error(
                            "Mail could not be send due to server error, please contact support."
                        )
            return {"succes": "Password has been updated."}

    @uweb3.decorators.loggedin
    @uweb3.decorators.checkxsrf
    @uweb3.decorators.TemplateParser("apisettings.html")
    def RequestApiSettings(self):
        """Returns the api settings page."""
        currentkeys = list(login_model.Apiuser.List(self.connection))

        # handle api key updates
        keys = []
        if self.post:
            deleted = self.post.getfirst("delete", {})
            updates = {
                "name": self.post.getfirst("name", {}),
                "collectionfilter": self.post.getfirst("collectionfilter", {}),
                "active": self.post.getfirst("active", {}),
            }
            for key in currentkeys:
                keyid = str(key["ID"])
                if keyid in deleted:
                    key.Delete()
                else:
                    for field in ("name", "collectionfilter"):
                        if keyid in updates[field]:
                            key[field] = updates[field][keyid]
                    key["active"] = "false"
                    if keyid in updates["active"]:
                        key["active"] = "true"
                    key.Save()
                    keys.append(key)
        else:
            keys = currentkeys

        # handle password change
        if "password" in self.post or "password_confirm" in self.post:
            password = self.post.getfirst("password", "")
            password_confirm = self.post.getfirst("password_confirm", "")
            if password != password_confirm:
                return {"error": "Passwords do not match, try again.", "keys": keys}
            try:
                self.user.UpdatePassword(password)
            except ValueError:
                return {"error": "Passwords too short.", "keys": keys}
            else:
                content = self.parser.Parse(
                    "email/updateuser.txt", email=self.user["email"]
                )
                try:
                    with mail.MailSender(
                        local_hostname=self.options["general"]["host"]
                    ) as send_mail:
                        send_mail.Text(
                            self.user["email"], "Warehouse account change", content
                        )
                except mail.SMTPConnectError:
                    if not self.debug:
                        return self.Error(
                            "Mail could not be send due to server error, please contact support."
                        )
            return {"succes": "Password has been updated.", "keys": keys}

        # handle new api key creation
        if "new_name" in self.post and len(self.post.getfirst("new_name")) > 0:
            try:
                newkey = login_model.Apiuser.Create(
                    self.connection, {"name": self.post.getfirst("new_name")}
                )
                keys.append(newkey)
            except common_model.InvalidNameError:
                return {
                    "keys": keys,
                    "apierror": "Provide a valid name for the new API key.",
                }
            except self.connection.IntegrityError:
                return {
                    "keys": keys,
                    "apierror": "That name was already used for another key.",
                }
            return {
                "keys": keys,
                "apisucces": 'Your new API key is: "%s".' % newkey["key"],
            }
        return {"keys": keys}

    @uweb3.decorators.loggedin
    def RequestIndex(self):
        """Returns the homepage"""
        return self.req.Redirect("/products")

    @uweb3.decorators.loggedin
    @uweb3.decorators.TemplateParser("gs1.html")
    def RequestGS1(self):
        """Returns the gs1 page"""
        products = PagedResult(
            self.pagesize,
            self.get.getfirst("page", 1),
            product_model.Product.List,
            self.connection,
            {"conditions": ["gs1 is not null"], "order": [("gs1", False)]},
        )
        return {"products": products}

    @uweb3.decorators.loggedin
    @uweb3.decorators.TemplateParser("ean.html")
    def RequestEAN(self):
        """Returns the EAN page"""
        products = PagedResult(
            self.pagesize,
            self.get.getfirst("page", 1),
            product_model.Product.List,
            self.connection,
            {
                "conditions": ["(gs1 is not null or ean is not null)"],
                "order": [("ean", False)],
            },
        )
        return {"products": products}

    @uweb3.decorators.checkxsrf
    @uweb3.decorators.TemplateParser("setup.html")
    def RequestSetup(self):
        """Allows the user to setup various fields, and create an admin user.

        If these fields are already filled out, this page will not function any
        longer.
        """
        if not login_model.User.IsFirstUser(self.connection):
            return self.RequestLogin()

        if (
            "email" in self.post
            and "password" in self.post
            and "password_confirm" in self.post
            and self.post.getfirst("password") == self.post.getfirst("password_confirm")
        ):
            try:
                user = login_model.User.Create(
                    self.connection,
                    {
                        "ID": 1,
                        "email": self.post.getfirst("email"),
                        "active": "true",
                        "password": self.post.getfirst("password"),
                    },
                    generate_password_hash=True,
                )
            except ValueError:
                return {"error": "Password too short, 8 characters minimal."}

            login_model.Session.Create(self.connection, int(user), path="/")

            self.config.Create("general", "host", self.post.getfirst("hostname"))
            self.config.Create(
                "general", "locale", self.post.getfirst("locale", "en_GB")
            )
            login_model.Session.Create(self.connection, int(user), path="/")
            return self.req.Redirect("/", httpcode=301)
        if self.post:
            return {"error": "Not all fields are properly filled out."}

    def XSRFInvalidToken(self):
        """Show that the users XSRF token is b0rked"""
        return self.Error("Your session has expired.", 403)

    def RequestInvalidcommand(self, command=None, error=None, httpcode=404):
        """Returns an error message"""
        if "api" in self.req.path:
            return self.RequestInvalidJsoncommand(command, httpcode)
        uweb3.logging.warning(
            "Bad page %r requested with method %s", command, self.req.method
        )
        if command is None and error is None:
            command = "%s for method %s" % (self.req.path, self.req.method)
        page_data = self.parser.Parse("404.html", command=command, error=error)
        return uweb3.Response(content=page_data, httpcode=httpcode)

    @uweb3.decorators.ContentType("application/json")
    def RequestInvalidJsoncommand(self, command, httpcode=404):
        """Returns an error message"""
        uweb3.logging.warning("Bad json page %r requested", command)
        return uweb3.Response(content={"error": command}, httpcode=httpcode)

    def Error(self, error="", httpcode=500, link=None):
        """Returns a generic error page based on the given parameters."""
        uweb3.logging.error("Error page triggered: %r", error)
        page_data = self.parser.Parse("error.html", error=error, link=link)
        return uweb3.Response(content=page_data, httpcode=httpcode)
