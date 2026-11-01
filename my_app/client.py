"""Client for a web API: the only module that talks to the network.

Keeping every network call in this one file has three benefits:

* The rest of the app never needs to know how the API works. It calls a
  method here and gets a plain Python dictionary back.
* Every network failure becomes one error type, `ApiError`, so the rest of
  the app needs only one `except` for all of them.
* Tests can replace `requests.get` with a fake, so they run without a
  network connection, without credentials and without depending on the API
  being up. This matters for continuous integration, which has none of
  those things.

WHAT TO BUILD FIRST (importance ranking)
----------------------------------------
Starting from scratch, or building a simple version? Build in this order.
Each level works on its own, and the next level makes it safer or nicer.
Every element in this file carries a matching tag in a comment, so you can
search for the tag (for example "[CORE]") to find it.

1. [CORE] The smallest working client: `requests.get(url, timeout=...)`,
   then `response.raise_for_status()`, then `response.json()`. These three
   calls inside `ApiClient.get_json`, plus `DEFAULT_TIMEOUT`, `__init__`
   and `build_url`, are a working client. Build and test this first.
2. [ERRORS] One `ApiError` and the `try`/`except` blocks that turn every
   failure (timeout, no connection, bad status, bad JSON) into it. Add this
   second, so the rest of the app has one thing to catch.
3. [SAFETY] Check input before it reaches the network: `ITEM_ID_PATTERN`,
   `InvalidItemIdError`, `validate_item_id` and `quote`. Add this third,
   whenever any part of the address comes from a user.
4. [SECONDARY] Nice to have, added when the real API needs them: the
   `logger` calls, the `auth` argument and the `params` argument.
5. [EXAMPLE] `EXAMPLE_BASE_URL` and `ApiClient.lookup` are the pretend API.
   Replace them with your real address and endpoints; keep everything above.

The example in `ApiClient.lookup` talks to a pretend API at
https://api.example.org/. To use a real API, change the base URL, the
endpoint path and the ID rule, and keep the structure.
"""

# `re` is Python's regular-expression module, used to check the shape of text.
import re

# `quote` makes a piece of text safe to place inside a web address.
from urllib.parse import quote

# `requests` is the library that makes web requests. Its version is pinned
# in pyproject.toml so that the app behaves the same on every computer.
import requests

# The shared logger from logger.py. Importing it here means messages from
# this file go to the same terminal and log file as everything else, with
# the same format and with secrets hidden.
from my_app.logger import logger

# [CORE] Without a timeout the app can freeze forever, so this is level 1.
# How many seconds to wait for the server before giving up.
# Without a timeout, `requests` waits forever, so one stuck server would
# freeze the whole app. Raise this number if the real API is slow.
DEFAULT_TIMEOUT = 30

# [EXAMPLE] Replace with the real API address.
# A placeholder address. `example.org` is reserved for examples, so this can
# never reach a real service by accident.
EXAMPLE_BASE_URL = "https://api.example.org/"

# [SAFETY] Level 3: input checking, before anything is sent.
# What an item ID may look like: 1 to 50 letters, digits, dots, colons,
# underscores or hyphens. For example "ABC123", "NM_000088.3" or "HGNC:5".
# Checking the shape before sending anything means a typo costs no network
# traffic, and text that could change the meaning of a web address (such as
# "/" or "?") never gets as far as the request.
ITEM_ID_PATTERN = re.compile(r"[A-Za-z0-9_.:-]{1,50}")


# [ERRORS] Level 2: one error type for every kind of failure.
class ApiError(Exception):
    """Raise when a request to the API fails, whatever the reason.

    Callers only need to catch this one error type. The original error from
    `requests` is kept as `__cause__`, so no detail is lost.
    """


# [SAFETY] Level 3: the error for input that fails the check.
class InvalidItemIdError(ValueError):
    """Raise when an item ID is not in the expected format.

    It is raised before any request is made. It is a kind of `ValueError`,
    which is what Python code normally raises for a value of the right type
    but with unacceptable content.
    """


# [SAFETY] Level 3: the check itself. Rename and change the rule for your IDs.
def validate_item_id(item_id):
    """Check that an item ID has the expected format.

    Parameters
    ----------
    item_id : str
        The ID to check.

    Returns
    -------
    str
        The same ID, so the call can be used inside an expression.

    Raises
    ------
    InvalidItemIdError
        When the ID is not a string of 1 to 50 allowed characters.
    """
    # A pure function like this one has no network or Flask in it, so it is
    # easy to test with many inputs.
    # `isinstance` comes first because the pattern can only match text: None
    # or a number would otherwise cause a TypeError, not our clear message.
    # `fullmatch` requires the WHOLE text to fit the pattern. (`match` with
    # "$" would wrongly accept "abc\n", because "$" also matches just before
    # a trailing newline.)
    if not isinstance(item_id, str) or not ITEM_ID_PATTERN.fullmatch(item_id):
        # Cut the value to 60 characters so a huge bad value cannot flood the
        # error message or the log. `!r` shows it with quotes, so spaces and
        # empty values are visible.
        shown = str(item_id)[:60]
        raise InvalidItemIdError(
            f"Invalid item ID {shown!r}. Use 1 to 50 letters, digits, dots, "
            "colons, underscores or hyphens."
        )
    return item_id


# [CORE] Level 1: the class holds the settings (address, timeout, login) that
# every request shares.
class ApiClient:
    """Make requests to one web API and return the data as Python objects.

    Parameters
    ----------
    base_url : str, optional
        The address all paths are added to, for example
        "https://api.example.org/". A missing final "/" is added.
    timeout : float, optional
        Seconds to wait for a reply before giving up.
    auth : tuple of str, optional
        A (user name, password) pair sent as HTTP basic authentication.
        Get it from `my_app.config.load_credentials()`, never type it in
        code. For an API that uses tokens, add a method that fetches the
        token and passes it in a header.
    """

    def __init__(
        self, base_url=EXAMPLE_BASE_URL, timeout=DEFAULT_TIMEOUT, auth=None
    ):
        # [CORE] `auth` is [SECONDARY]: leave it out for an open API.
        # `self.name = value` stores the value on this one client object, so
        # every method can use it later as `self.name`.
        # Make sure the address ends in exactly one "/". Then a path can be
        # added by simple joining, with no risk of "//" or a missing "/".
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.auth = auth

    # [CORE] Level 1: joins the base address and a path.
    def build_url(self, path):
        """Return the full web address for a path on this API.

        Parameters
        ----------
        path : str
            The part after the base address, such as "items/ABC123".

        Returns
        -------
        str
            The base address followed by the path.
        """
        # `lstrip("/")` removes any leading "/" from the path, because the
        # base address already ends in one.
        return self.base_url + path.lstrip("/")

    # [CORE] Level 1: the heart of the file. The three calls that matter are
    # `requests.get`, `raise_for_status` and `json`. Everything else in this
    # method is level 2 ([ERRORS]) or level 4 ([SECONDARY]) and can be added
    # after the simple version works. `params` is [SECONDARY].
    def get_json(self, path, params=None):
        """Send a GET request and return the reply as Python data.

        Parameters
        ----------
        path : str
            The part of the address after the base address.
        params : dict, optional
            Query-string values, for example {"build": "GRCh38"}. `requests`
            encodes them safely, so do not build "?a=b" by hand.

        Returns
        -------
        dict or list
            The JSON in the reply, converted to Python objects.

        Raises
        ------
        ApiError
            When the request times out, cannot connect, gets an HTTP error
            status (such as 404 or 500), or the reply is not valid JSON.
        """
        url = self.build_url(path)
        # [SECONDARY] Logging. Useful, but the client works without it.
        # Log the address WITHOUT the query string or credentials: tokens
        # and keys are often sent as query values, and a log file is easy
        # to share by accident.
        logger.debug(f"GET {url}")

        try:
            response = requests.get(
                url, params=params, auth=self.auth, timeout=self.timeout
            )
            # `raise_for_status` turns a 4xx or 5xx reply into an exception.
            # Without it, a "404 Not Found" page would look like success.
            response.raise_for_status()
        # Order matters: `Timeout` is a kind of `RequestException`, so it
        # must be caught first to get its own, more helpful, message.
        except requests.exceptions.Timeout as error:
            logger.error(f"Request to {url} timed out: {error}")
            # `from error` keeps the original error attached as the cause,
            # so the log still shows what really happened.
            raise ApiError(
                f"The API did not reply within {self.timeout} seconds."
            ) from error
        # `RequestException` is the parent of every `requests` error:
        # connection failures, bad status codes, invalid addresses and so on.
        except requests.exceptions.RequestException as error:
            # The error text can contain the full address, query string
            # included. The logger hides secrets it recognises, but the
            # safest habit is to send secrets in `auth` or a header, not in
            # `params`.
            logger.error(f"Request to {url} failed: {error}")
            raise ApiError(
                f"The request to the API failed: {error}"
            ) from error

        try:
            return response.json()
        # `json()` raises a ValueError (or a subclass) when the reply is not
        # valid JSON, for example an HTML error page from a proxy.
        except ValueError as error:
            logger.error(f"Reply from {url} was not valid JSON")
            raise ApiError("The API reply was not valid JSON.") from error

    # [EXAMPLE] A pretend endpoint. Replace with your real ones; each real
    # endpoint becomes one short method like this that calls `get_json`.
    def lookup(self, item_id):
        """Fetch one item by its ID. This is the example endpoint.

        Parameters
        ----------
        item_id : str
            The ID to look up, for example "ABC123".

        Returns
        -------
        dict
            The item, as given by the API.

        Raises
        ------
        InvalidItemIdError
            When the ID has the wrong format. No request is made.
        ApiError
            When the request fails (see `get_json`).
        """
        # [SAFETY] Level 3. Check the input first: it is cheap, local, and
        # gives the clearest error.
        item_id = validate_item_id(item_id)
        logger.info(f"Looking up {item_id}")
        # `quote(..., safe="")` encodes every character that has a special
        # meaning in an address, "/" and ":" included. The ID rule above
        # already excludes most of them, but the path is built from user
        # input, so encoding it as well is a second layer of protection.
        return self.get_json(f"items/{quote(item_id, safe='')}")
