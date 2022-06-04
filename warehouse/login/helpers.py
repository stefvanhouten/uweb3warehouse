import uweb3

from warehouse.login import model


class LoginService:
    def __init__(self, connection):
        """Setup the LoginService class.

        Args:
            connection (PageMaker.connection): The connection to the database.
        """
        self._user = None
        self._auth_failed = False  # Used to prevent attempting to authenticate a failed user multiple times.
        self.connection = connection
        self.session = model.Session(self.connection)

    def authenticate(self):
        """Authenticate the user based on the session cookie.

        Attempts to find a userID in the cookie object, if a userID is found then attempt
        to retrieve the user from the database. When no user is found, or the cookie is invalid
        throw a ValueError.

        After failing authentication, the session cookie is deleted.
        On successful authentication, remember the user and prevent accessing the database again.
        Since this Service is not persistent between requests the user is only authenticated for the current request.

        Raises:
            ValueError: When no user is found, or the cookie is invalid a ValueError is raised.

        Returns:
            model.User: A user object.
        """
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
        """Gets the userID from the cookie.

        Attempts to read the cookie and convert the stored userID to an integer.
        When the cookie is invalid or the userID is not an integer a ValueError is raised and the cookie is deleted.

        Raises:
            ValueError: When the cookie is invalid or the userID is not an integer.

        Returns:
            int: The userID from the cookie.
        """
        try:
            userID = int(str(self.session.rawcookie))
        except Exception as ex:
            self._fail_authentication()
            raise ValueError("Session cookie invalid") from ex
        return userID

    def _get_user(self, userID):
        """Returns the User from the database if the user is found, otherwise None is returned.

        When the user is not found in the database delete the cookie and return None.

        Args:
            userID (int): The userID to retrieve the user from the database.

        Returns:
            model.User: The User object.
        """
        try:
            return model.User.FromPrimary(self.connection, userID)
        except uweb3.model.NotExistError:
            self._fail_authentication()
        return None

    def _fail_authentication(self):
        """When something goes wrong during authentication, delete the cookie and set the auth_failed flag to true."""
        self._auth_failed = True
        self.session.Delete()


class LoginServiceBuilder:
    def __init__(self):
        self._instance = None

    def __call__(self, connection, **ignored):
        """Setup the LoginService when no instance exists, otherwise return the existing instance

        Args:
            connection (PageMaker.connection): The connection object that the service uses.

        Returns:
            LoginService: The LoginService instance
        """
        if not self._instance:
            self._instance = LoginService(connection)
        return self._instance


class ApiUserService:
    def __init__(self, connection, apikey):
        """Setup the ApiUserService class.

        Args:
            connection (PageMaker.connection): The connection to the database.
            apikey (str): The API key that needs to be validated.
        """
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
        """Setup for the ApiUserService when no instance exists, otherwise return the existing instance.

        Args:
            connection (PageMaker.connection): The connection object that the service uses.
            apikey (str): The apikey provided by the user attempting to gain access to the API.

        Returns:
            ApiUserService: The ApiUserService instance.
        """
        if not self._instance:
            self._instance = ApiUserService(connection, apikey)
        return self._instance


class AuthFactory:
    """Factory class for authentication services.

    This class is used to registrate the different authentication services
    that are available within the project. Each service provides a way to
    validate that a user has certain priveleges or is allowed to access the resources
    on the page.
    """

    def __init__(self):
        self._authenticators = {}

    def register_auth(self, key, builder):
        """Registers an new authentication service with the AuthFactory class.

        Args:
            key (str): The name of the authentication service.
            builder: The builder class for the given authentication service.
                    The builder class is used to supply the Service class with the correct
                    attributes on call. The builder class must have a __call__ method
                    that supplies the service with the provided arguments.
        """
        self._authenticators[key] = builder

    def get_authenticator(self, key, **kwargs):
        """Retrieve an authentication service by name.

        Args:
            key (str): The name of the service by which it was registered.

        Raises:
            ValueError: Raised when the service could not be found in the registered authenticators.

        Returns:
            _type_: An authentication service.
        """
        builder = self._authenticators.get(key)
        if not builder:
            raise ValueError(key)
        return builder(**kwargs)


class AuthMixin:
    def __init__(self, *args, **kwargs):
        """PageMaker mixin that behaves like uweb3.LoginMixin but allows registration of authentication services."""
        self._user = None
        self.auth_services = AuthFactory()

    @property
    def user(self):
        """Returns the current user or false if no user is logged in, or the user validation failed.

        Uses the login authentication service to validate the user.

        Returns:
            model.User: User object containing all relevant user data.
        """
        if not self._user:
            authenticator = self.auth_services.get_authenticator("login", connection=self.connection)  # type: ignore
            try:
                self._user = authenticator.authenticate()
            except ValueError:
                self._user = False
        return self._user
