"""Flask application factory for My App.

`create_app` sets up logging and defines the home and search routes.

The app is created inside `create_app`, not when the module is imported,
so that tests can create their own copy.
"""

from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException

from my_app.logger import logger, setup_logging
from my_app.modules.example import clean_query


def create_app():
    """Create and configure the Flask application.

    Returns
    -------
    Flask
        The configured application.
    """
    app = Flask(__name__)
    # Set up logging first, so that every message below is recorded.
    setup_logging()
    logger.info("Initialising Flask application")

    @app.route("/")
    def home():
        """Render the home page.

        Returns
        -------
        str
            The search page HTML.
        """
        logger.debug("Rendering home page")
        return render_template("index.html")

    @app.route("/search", methods=["POST"])
    def search():
        """Handle a search request.

        Returns
        -------
        str
            The page showing the result, or an error message if the
            query is empty.
        """
        # A missing form field gives None, which clean_query rejects.
        try:
            query = clean_query(request.form.get("query"))
        except ValueError:
            logger.warning("No input provided")
            return render_template(
                "index.html", error="Error: No input provided", result=None
            )
        logger.info(f"Search for {query}")
        return render_template("index.html", error=None, result=query)

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
        if isinstance(error, HTTPException):
            return error
        logger.exception(
            f"Unexpected error handling {request.method} {request.path}"
        )
        return (
            render_template(
                "index.html",
                error="Error: Something went wrong. Please try again.",
                result=None,
            ),
            500,
        )

    return app
