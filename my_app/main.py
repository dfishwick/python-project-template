"""Flask application factory for My App.

`create_app` sets up logging and defines the home and search routes.

The app is created inside `create_app`, not when the module is imported,
so that tests can create their own copy. This is called the "application
factory" pattern. Flask's own documentation recommends it, and it is what
lets `tests/conftest.py` build a fresh app for every test.

WHAT TO BUILD FIRST (importance ranking)
----------------------------------------
Starting from scratch, or building a simple version? Build in this order.
Each element below carries a matching tag in a comment, so you can search
this file for the tag (for example "[CORE]") to find it.

1. [CORE] `create_app` with `Flask(__name__)`, one route that returns
   `render_template(...)`, and `return app`. That is a working web app.
2. [CORE] A second route that reads form data (`request.form`) and calls a
   plain function. Keep the real work in `modules/`, not in the route.
3. [ERRORS] Handle bad input (`except ValueError`) and unexpected failures
   (`errorhandler`), so users see a message and not a crash.
4. [SECONDARY] Logging: `setup_logging()` and the `logger` calls. Add them
   as soon as the first version runs, because they help every later step.
5. [EXAMPLE] `clean_query`, the page text and the "search" idea itself are
   the pretend project. Replace them with the real one.
"""

# `Flask` is the web framework. `render_template` fills an HTML file from
# the `templates/` folder. `request` holds the data sent by the browser.
from flask import Flask, render_template, request

# The base class of "normal" web errors such as 404 Not Found.
from werkzeug.exceptions import HTTPException

# [SECONDARY] The shared logger and the function that configures it.
from my_app.logger import logger, setup_logging

# [EXAMPLE] The pretend project logic. Replace with your own functions.
from my_app.modules.example import clean_query


# [CORE] Level 1: the factory. Everything the app needs is created and
# connected inside this one function.
def create_app():
    """Create and configure the Flask application.

    Returns
    -------
    Flask
        The configured application.
    """
    # [CORE] `__name__` tells Flask where this module lives, so it can find
    # the `templates/` and `static/` folders next to it.
    app = Flask(__name__)
    # [SECONDARY] Set up logging first, so that every message below is
    # recorded.
    setup_logging()
    logger.info("Initialising Flask application")

    # [CORE] Level 1: a route. `@app.route("/")` registers the function
    # below it for the address "/" (the home page). The function name is
    # also used internally by Flask, so each route needs a different one.
    @app.route("/")
    def home():
        """Render the home page.

        Returns
        -------
        str
            The search page HTML.
        """
        logger.debug("Rendering home page")
        # `render_template` loads templates/index.html and returns the
        # finished HTML text. Flask sends that text to the browser.
        return render_template("index.html")

    # [CORE] Level 2: a route that receives form data. `methods=["POST"]`
    # means it only answers when a form is submitted, not when someone
    # types the address into the browser.
    @app.route("/search", methods=["POST"])
    def search():
        """Handle a search request.

        Returns
        -------
        str
            The page showing the result, or an error message if the
            query is empty.
        """
        # [ERRORS] Level 3: expected bad input is handled here, close to
        # where it happens.
        # `request.form.get("query")` reads the form field called "query".
        # A missing field gives None (not an error), which clean_query
        # rejects with a ValueError, so one `except` covers both cases.
        try:
            query = clean_query(request.form.get("query"))
        except ValueError:
            logger.warning("No input provided")
            # Show the same page again with an error message. Keeping the
            # user on the page they were on is friendlier than an error
            # screen.
            return render_template(
                "index.html", error="Error: No input provided", result=None
            )
        logger.info(f"Search for {query}")
        # [EXAMPLE] The "result" is just the cleaned query echoed back.
        # Replace with the real output of your project.
        return render_template("index.html", error=None, result=query)

    # [ERRORS] Level 3: a safety net for anything not expected. Without it,
    # an unexpected bug would show Flask's default error page and the log
    # would not record what happened. `Exception` catches every error type.
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Log an unexpected error and show a simple error page.

        Parameters
        ----------
        error : Exception
            The exception raised while handling the request.

        Returns
        -------
        str or werkzeug.exceptions.HTTPException
            Normal HTTP errors such as 404 are returned unchanged.
            Anything else gives the search page with an error message
            and status code 500.
        """
        # Pages not found (404) and similar are normal, not unexpected.
        # Returning the error unchanged lets Flask show its usual page.
        if isinstance(error, HTTPException):
            return error
        # `logger.exception` logs at ERROR level AND includes the full
        # traceback. Only use it inside an `except` block or a handler like
        # this one, where there is a current exception to describe.
        logger.exception(
            f"Unexpected error handling {request.method} {request.path}"
        )
        # A tuple of (body, status code). 500 means "server error", so
        # browsers, monitors and tests can tell this was a failure. The
        # message is deliberately vague: details belong in the log, not on
        # a page every visitor can see.
        return (
            render_template(
                "index.html",
                error="Error: Something went wrong. Please try again.",
                result=None,
            ),
            500,
        )

    # [CORE] Hand back the finished app. Without this line, the caller
    # (the run command, or a test) would receive None.
    return app
