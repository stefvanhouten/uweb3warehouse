import uweb3

from warehouse.login import model


class LoginService:
    def __init__(self, connection):
        self._auth_failed = False
        self._user = None
        self.connection = connection

    def authenticate(self):
        if self._auth_failed:
            raise ValueError("Authentication failed")

        if not self._user and not self._auth_failed:
            try:
                session = model.Session(self.connection)
                userID = int(str(session.rawcookie))
            except Exception as ex:
                self._auth_failed = True
                session.Delete()
                raise ValueError("Session cookie invalid") from ex

            try:
                self._user = model.User.FromPrimary(self.connection, userID)
            except uweb3.model.NotExistError:
                self._auth_failed = True

        if not self._user:
            raise ValueError("User not valid")

        if self._user["active"] != "true":
            raise ValueError("User not active, session invalid")
        return self._user


class LoginServiceBuilder:
    def __init__(self):
        self._instance = None

    def __call__(self, connection, **ignored):
        if not self._instance:
            self._instance = LoginService(connection)
        return self._instance


class AdminService:
    def __init__(self, connection, user):
        self._user = user
        self._admin = None
        self.connection = connection

    def authenticate(self):
        if not self._admin:
            if self._user["admin"] != "true":
                raise ValueError("User not admin")
        return self._admin


class AdminServiceBuilder:
    def __init__(self):
        self._instance = None

    def __call__(self, connection, user, **ignored):
        if not self._instance:
            self._instance = AdminService(connection, user)
        return self._instance


class AuthFactory:
    def __init__(self):
        self._authenticators = {}

    def register_auth(self, key, builder):
        self._authenticators[key] = builder

    def get_authenticator(self, key, **kwargs):
        builder = self._authenticators.get(key)
        if not builder:
            raise ValueError(key)
        return builder(**kwargs)


class AuthMixin:
    def __init__(self, *args, **kwargs):
        self._user = None
        self.auth_services = AuthFactory()

    @property
    def user(self):
        """Returns the current user"""
        if not self._user:
            authenticator = self.auth_services.get_authenticator("login", connection=self.connection)  # type: ignore
            self._user = authenticator.authenticate()
        return self._user
