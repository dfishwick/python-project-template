"""Load API credentials from outside the repository.

Credentials are never kept in the code or in Git. They are read from
environment variables, or from a private file in the user's home folder.
An environment variable wins over the file, so Docker and CI can supply
credentials without a file.
"""

import configparser
import os
from pathlib import Path

from my_app.logger import logger, register_secret

CREDENTIALS_FILE = Path.home() / ".my_app_access" / "credentials.ini"
SECTION = "api"
EMAIL_VAR = "MY_APP_API_EMAIL"
PASSWORD_VAR = "MY_APP_API_PASSWORD"


class ConfigError(Exception):
    """Raise when credentials are missing or the file cannot be read."""


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
        parser.read(path, encoding="utf-8")
    except configparser.Error:
        # The parser's own message can quote the line it failed on, and
        # that line may be the password. Say where, not what.
        raise ConfigError(
            f"Could not read {path}. Check that it has an [{SECTION}] "
            "section with email and password lines."
        ) from None
    values = {}
    for key in ("email", "password"):
        value = parser.get(SECTION, key, fallback=None)
        if value:
            values[key] = value
    return values


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
    # An environment variable wins, so Docker and CI need no file.
    email = os.environ.get(EMAIL_VAR) or from_file.get("email")
    password = os.environ.get(PASSWORD_VAR) or from_file.get("password")

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

    # Register before anything else can log the password.
    register_secret(password)
    logger.info("Loaded API credentials")
    return email, password
