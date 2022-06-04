from http import HTTPStatus

import uweb3

from warehouse.login import model


def NotExistsErrorCatcher(f):
    """Decorator to return a 404 if a NotExistError exception was returned."""

    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except uweb3.model.NotExistError as error:
            return args[0].RequestInvalidcommand(error=error)

    return wrapper


def apiuser(f):
    """Decorator to check if the given API key is allowed to access the resource."""

    def wrapper(pagemaker, *args, **kwargs):
        # This is bypassed if a user is already logged in trough a session
        if pagemaker.user or pagemaker.api_user:
            return f(pagemaker, *args, **kwargs)
        apikey = None

        if "apikey" in pagemaker.get:
            apikey = pagemaker.get.getfirst("apikey")
        elif "apikey" in pagemaker.post:
            apikey = pagemaker.post["apikey"]
        elif "apikey" in pagemaker.req.headers:
            apikey = pagemaker.req.headers.get("apikey")

        authenticator = pagemaker.auth_services.get_authenticator(
            "apiuser", connection=pagemaker.connection, apikey=apikey
        )
        try:
            pagemaker.apikey = apikey
            pagemaker.api_user = authenticator.authenticate()
        except ValueError as apierror:
            return uweb3.Response(content={"error": str(apierror)}, httpcode=403)
        return f(pagemaker, *args, **kwargs)

    return wrapper


def json_error_wrapper(func):
    def wrapper_schema_validation(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return uweb3.Response(
                {
                    "error": True,
                    "errors": e.args,
                    "http_status": HTTPStatus.NOT_FOUND,
                },
                httpcode=HTTPStatus.NOT_FOUND,
            )
        except uweb3.model.NotExistError as msg:
            return uweb3.Response(
                {
                    "error": True,
                    "errors": msg.args,
                    "http_status": HTTPStatus.NOT_FOUND,
                },
                httpcode=HTTPStatus.NOT_FOUND,
            )
        except Exception as err:
            print(err)
            return uweb3.Response(
                {
                    "error": True,
                    "errors": ["Something went wrong!"],
                    "http_status": HTTPStatus.INTERNAL_SERVER_ERROR,
                },
                httpcode=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    return wrapper_schema_validation


def loggedin(f):
    """Decorator that checks if the user requesting the page is logged in based on set cookie."""

    def wrapper(pagemaker, *args, **kwargs):
        if not pagemaker.user:
            return uweb3.Redirect("/login", httpcode=303)
        return f(pagemaker, *args, **kwargs)

    return wrapper
