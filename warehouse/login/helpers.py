import uweb3

from warehouse.login import model


class LoginService:
    def __init__(self, connection):
        self._user = None
        self._auth_failed = False
        self.connection = connection
        self.session = model.Session(self.connection)

    def authenticate(self):
        if self._auth_failed:
            raise ValueError("Authentication failed")

        if not self._user and not self._auth_failed:
            userID = self._get_userid_from_cookie()
            self._user = self._get_user(userID)

        if not self._user:
            raise ValueError("User not valid")

        if self._user["active"] != "true":
            raise ValueError("User not active, session invalid")
        return self._user

    def _get_userid_from_cookie(self):
        try:
            userID = int(str(self.session.rawcookie))
        except Exception as ex:
            self._fail_authentication()
            raise ValueError("Session cookie invalid") from ex
        return userID

    def _get_user(self, userID):
        try:
            return model.User.FromPrimary(self.connection, userID)
        except uweb3.model.NotExistError:
            self._fail_authentication()
        return None

    def _fail_authentication(self):
        self._auth_failed = True
        self.session.Delete()


class LoginServiceBuilder:
    def __init__(self):
        self._instance = None

    def __call__(self, connection, **ignored):
        if not self._instance:
            self._instance = LoginService(connection)
        return self._instance


class ApiUserService:
    def __init__(self, connection, apikey):
        self.apikey = apikey
        self._instance = None
        self.connection = connection

    def authenticate(self):
        if not self._instance:
            self._instance = self._get_user()
        return self._instance

    def _get_user(self):
        try:
            return model.Apiuser.FromKey(self.connection, self.apikey)
        except uweb3.model.NotExistError as ex:
            raise ValueError("The given API key is not valid") from ex


class ApiUserServiceBuilder:
    def __init__(self):
        self._instance = None

    def __call__(self, connection, apikey, **ignored):
        if not self._instance:
            self._instance = ApiUserService(connection, apikey)
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
            try:
                self._user = authenticator.authenticate()
            except ValueError:
                self._user = False
        return self._user
