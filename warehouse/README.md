# µWeb3 warehuse application scaffold

This is an empty µWeb3 base project that serves as the starting point for your
project. The following parts are included and allow for easy extension:

* µWeb3 request routing and server setup (in `__init__.py`)
* a basic configuration file that is read upon app start (`config.ini`)
* use of PageMaker (in 'pages.py') and example template usage (templates in `templates/`)
* included Apache WSGI configuration and development server runner.

# How to run

* Run `serve.py` from the commandline
* Use the included `base.wsgi` script to set up Apache + mod_wsgi
