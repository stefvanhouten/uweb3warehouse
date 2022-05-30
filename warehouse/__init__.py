"""A uWeb3 warehousing inventory software."""
import os

# Third-party modules
import uweb3

from warehouse.login.urls import urls as login_urls
from warehouse.products.urls import urls as product_urls
from warehouse.suppliers.urls import urls as supplier_urls

# Application
from . import basepages


def main():
    """Creates a uWeb3 application.

    The application is created from the following components:

    - The presenter class (PageMaker) which implements the request handlers.
    - The routes iterable, where each 2-tuple defines a url-pattern and the
      name of a presenter method which should handle it.
    - The execution path, internally used to find templates etc.
    """
    return uweb3.uWeb(
        basepages.PageMaker,
        supplier_urls
        + product_urls
        + login_urls
        + [
            ("/", "RequestIndex"),
            ("/setup", "RequestSetup"),
            ("/admin", "RequestAdmin"),
            # Helper files
            ("(/styles/.*)", "Static"),
            ("(/js/.*)", "Static"),
            ("(/media/.*)", "Static"),
            ("(/favicon.ico)", "Static"),
            ("(/.*)", "RequestInvalidcommand"),
        ],
        os.path.dirname(__file__),
    )
