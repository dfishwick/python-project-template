"""Load API credentials from outside the repository.

Credentials are never kept in the code or in Git. They are read from
environment variables, or from a private file in the user's home folder.
An environment variable wins over the file, so Docker and CI can supply
credentials without a file.

WHAT TO BUILD FIRST (importance ranking)
----------------------------------------
Starting from scratch, or building a simple version? Build in this order.
Each element carries a matching tag in a comment, so you can search this
file for the tag (for example "[CORE]") to find it.

1. [CORE] Read two values from environment variables with `os.environ.get`.
   That alone keeps credentials out of the code.
2. [CORE] A clear error (`ConfigError`) when a value is missing, naming
   which one, so the user knows what to fix.
3. [SECONDARY] A private credentials file in the home folder, read with
   `configparser`, for people who do not want to set variables every time.
4. [SAFETY] `register_secret`, so the password is hidden if it is ever
   logged, and `raise ... from None`, so a parser error cannot print it.
"""

# `configparser` reads INI files: lines like `email = a@b.org` under a
# heading such as `[api]`.
import configparser

# `os.environ` is a dictionary of the environment variables.
import os

from pathlib import Path

# [SAFETY] The shared logger, and the function that hides a secret in it.
from my_app.logger import logger, register_secret

# [SECONDARY] Level 3: where the private file lives. It is in the home folder,
# outside the repository, so `git add` can never pick it up.
CREDENTIALS_FILE = Path.home() / ".my_app_access" / "credentials.ini"
# The heading in the INI file: `[api]`.
SECTION = "api"
# [CORE] Level 1: the names of the environment variables.
EMAIL_VAR = "MY_APP_API_EMAIL"
PASSWORD_VAR = "MY_APP_API_PASSWORD"


# [CORE] Level 2: one error type for every credentials problem, so callers
# catch one thing.
class ConfigError(Exception):
    """Raise when credentials are missing or the file cannot be read."""


# [SECONDARY] Level 3: the file reader. It is separate from
# `load_credentials` so each can be tested on its own.
def read_credentials_file(path):
    """Read the email and password from a credentials file.

    Parameters
    ----------
    path : pathlib.Path
        The credentials file. It does not have to exist.

    Returns
    -------
    dict
        The values found, with the keys "email" and "password". Empty if
        the file, or its section, is missing.

    Raises
    ------
    ConfigError
        When the file exists but cannot be parsed.
    """
    parser = configparser.ConfigParser()
    try:
        # `read` quietly skips a file that does not exist. That is
        # intended: the environment variables may be supplying everything.
        parser.read(path, encoding="utf-8")
    except configparser.Error:
        # [SAFETY] The parser's own message can quote the line it failed on,
        # and that line may be the password. Say where, not what.
        # `from None` also drops the original error from the traceback, so
        # the quoted line cannot appear there either.
        raise ConfigError(
            f"Could not read {path}. Check that it has an [{SECTION}] "
            "section with email and password lines."
        ) from None
    values = {}
    for key in ("email", "password"):
        # `fallback=None` gives None, not an error, for a missing key or
        # section. A blank value is also skipped by the `if value` test.
        value = parser.get(SECTION, key, fallback=None)
        if value:
            values[key] = value
    return values


# [CORE] Levels 1 to 4: the function the rest of the app calls.
def load_credentials(path=None):
    """Return the API email and password, and hide the password in logs.

    Parameters
    ----------
    path : str or pathlib.Path, optional
        The credentials file. Defaults to `CREDENTIALS_FILE`.

    Returns
    -------
    tuple of str
        The email and the password.

    Raises
    ------
    ConfigError
        When the email or the password is in neither the environment nor
        the file, or when the file cannot be parsed.
    """
    path = Path(path) if path else CREDENTIALS_FILE
    from_file = read_credentials_file(path)
    # [CORE] An environment variable wins, so Docker and CI need no file.
    # `a or b` gives `b` when `a` is None or empty.
    email = os.environ.get(EMAIL_VAR) or from_file.get("email")
    password = os.environ.get(PASSWORD_VAR) or from_file.get("password")

    # [CORE] Level 2: collect EVERY missing item first, so the user fixes
    # them in one go and not one error at a time.
    missing = [
        name
        for name, value in ((EMAIL_VAR, email), (PASSWORD_VAR, password))
        if not value
    ]
    if missing:
        raise ConfigError(
            f"Missing {' and '.join(missing)}. Set the environment "
            f"variables, or add email and password under [{SECTION}] "
            f"in {path}."
        )

    # [SAFETY] Register before anything else can log the password.
    register_secret(password)
    # Note what is logged: the fact that credentials loaded, never the
    # values themselves.
    logger.info("Loaded API credentials")
    return email, password
