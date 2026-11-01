"""Logging setup for the app.

Messages go to the terminal (the stream) and to a rotating log file.
Each has its own level. The levels and the log file path can be set
with environment variables, see `setup_logging`.
"""

import logging
import os
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
DEFAULT_STREAM_LEVEL = "INFO"
DEFAULT_FILE_LEVEL = "DEBUG"
DEFAULT_LOG_DIR = Path.home() / ".my_app"
LOG_FILE_PREFIX = "my_app_"
MAX_BYTES = 500_000
BACKUP_COUNT = 5

logger = logging.getLogger("my_app")

REDACTED = "[REDACTED]"

# Each pair is (what to look for, what to put back). \1 keeps the text in
# the first brackets, such as "password=", and hides only the value after it.
SECRET_PATTERNS = [
    # Authorization: Bearer abc123    or    Authorization: Basic abc123
    (
        re.compile(
            r"(authorization[\"']?\s*[:=]\s*[\"']?)"
            r"(?:(?:bearer|basic)\s+)?[^\s,;\"']+",
            re.IGNORECASE,
        ),
        r"\1" + REDACTED,
    ),
    # password=abc   token: abc   "api_key": "abc"   SHAIP_PASSWORD=abc
    (
        re.compile(
            r"((?:password|passwd|secret|token|api[_-]?key)"
            r"[\"']?\s*[:=]\s*[\"']?)[^\s,;&\"']+",
            re.IGNORECASE,
        ),
        r"\1" + REDACTED,
    ),
    # https://user:password@example.org
    (
        re.compile(
            r"([a-z][a-z0-9+.-]*://)[^\s/@:]+:[^\s/@]+@", re.IGNORECASE
        ),
        r"\1" + REDACTED + "@",
    ),
]

_secrets = set()


def register_secret(value):
    """Hide an exact secret value wherever it appears in the logs.

    Call this once for each password or token the app loads, so the value
    is hidden even if it is written in a format the patterns do not know.

    Parameters
    ----------
    value : str
        The secret. Values shorter than 4 characters are ignored, because
        hiding them would damage ordinary log text.
    """
    if value and len(str(value)) >= 4:
        _secrets.add(str(value))


def redact(text):
    """Hide secrets in a piece of text.

    Parameters
    ----------
    text : str
        A log line, which may include a traceback.

    Returns
    -------
    str
        The text with registered secrets and secret-looking values
        replaced by `REDACTED`.
    """
    # Longest first, so a secret that contains another is hidden whole.
    for secret in sorted(_secrets, key=len, reverse=True):
        text = text.replace(secret, REDACTED)
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactingFormatter(logging.Formatter):
    """Format log records, then hide any secrets in the finished text."""

    def format(self, record):
        """Return the formatted record with secrets hidden."""
        return redact(super().format(record))


def resolve_level(argument, env_name, default):
    """Work out a log level from an argument, variable or default.

    Parameters
    ----------
    argument : str or None
        Level name passed in by the caller. Used first if given.
    env_name : str
        Name of the environment variable to use if `argument` is empty.
    default : str
        Level name used if neither of the above is set.

    Returns
    -------
    int
        The level as a number, e.g. logging.INFO.

    Raises
    ------
    ValueError
        When the level name is not one of `VALID_LEVELS`.
    """
    value = (argument or os.environ.get(env_name) or default).strip().upper()
    if value not in VALID_LEVELS:
        raise ValueError(
            f"{env_name} must be one of {', '.join(VALID_LEVELS)}, "
            f"not '{value}'"
        )
    # logging.DEBUG, logging.INFO and so on are numbers: look up by name.
    return getattr(logging, value)


def default_log_file(now=None):
    """Return the default log file, named with the date and time it was made.

    Reuse the newest existing log file in `DEFAULT_LOG_DIR`. If there is none,
    name a new one with the current date and time.

    Parameters
    ----------
    now : datetime.datetime, optional
        The time to use in the name of a new file. Defaults to the current
        time.

    Returns
    -------
    pathlib.Path
        For example `my_app_2026-11-01_04-25-00.log` inside
        `DEFAULT_LOG_DIR`.
    """
    # The date and time in the names sort oldest first, so the last is newest.
    existing = sorted(DEFAULT_LOG_DIR.glob(f"{LOG_FILE_PREFIX}*.log"))
    if existing:
        return existing[-1]
    now = now or datetime.now()
    # Hyphens, not colons, because Windows file names cannot contain ":".
    return DEFAULT_LOG_DIR / f"{LOG_FILE_PREFIX}{now:%Y-%m-%d_%H-%M-%S}.log"


def setup_logging(stream_level=None, file_level=None, log_file=None):
    """Send log messages to the terminal and to a rotating log file.

    Each value can be given as an argument, or set with an environment
    variable. If neither is set, the default is used.

    Parameters
    ----------
    stream_level : str, optional
        Level for the terminal. Environment variable
        MY_APP_STREAM_LOG_LEVEL, default INFO.
    file_level : str, optional
        Level for the log file. Environment variable
        MY_APP_FILE_LOG_LEVEL, default DEBUG.
    log_file : str or pathlib.Path, optional
        Path of the log file, used exactly as given. Environment variable
        MY_APP_LOG_FILE. If neither is set, the app uses the log file in
        `.my_app` in the user's home folder, named with the date and
        time it was first made (for example
        `my_app_2026-11-01_04-25-00.log`).

    Raises
    ------
    ValueError
        When a level name is not valid.
    """
    stream_level = resolve_level(
        stream_level, "MY_APP_STREAM_LOG_LEVEL", DEFAULT_STREAM_LEVEL
    )
    file_level = resolve_level(
        file_level, "MY_APP_FILE_LOG_LEVEL", DEFAULT_FILE_LEVEL
    )
    chosen_file = log_file or os.environ.get("MY_APP_LOG_FILE")
    log_path = Path(chosen_file) if chosen_file else default_log_file()

    # Let every message reach the handlers.
    # Each handler then applies its own level.
    logger.setLevel(logging.DEBUG)

    # Remove handlers from an earlier call so messages are not logged twice.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = RedactingFormatter("%(asctime)s - %(levelname)s - %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(stream_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # A problem with the log file should not stop the app from starting.
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError as error:
        logger.warning(
            f"Could not open log file {log_path}: {error}. "
            "Logging to the stream only."
        )
        return
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
