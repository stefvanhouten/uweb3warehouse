#!/usr/bin/python3
"""Starts a simple application development server.
Just execute `./serve.py` or `python3 serve.py`
"""

# Application
import warehouse


def main():
    app = warehouse.main()
    app.serve()


if __name__ == "__main__":
    main()
