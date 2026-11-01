"""Logging setup for the app.

Messages go to the terminal (the stream) and to a rotating log file.
Each has its own level. The levels and the log file path can be set
with environment variables, see `setup_logging`.

Why log at all? `print()` shows a message once, on screen, with no record
of when it happened or how serious it was. A logger adds a time, a level
and a destination, can write to a file, and can be turned up or down
without editing the code that uses it.

The log levels, from least to most serious:
DEBUG (detail for developers), INFO (normal events), WARNING (something
odd but handled), ERROR (something failed), CRITICAL (the app cannot go on).
A handler set to INFO shows INFO and everything more serious.

WHAT TO BUILD FIRST (importance ranking)
----------------------------------------
Starting from scratch, or building a simple version? Build in this order.
Each element carries a matching tag in a comment, so you can search this
file for the tag (for example "[CORE]") to find it.

1. [CORE] `logger = logging.getLogger("my_app")`, one handler with a
   formatter, and `setLevel`. Eight lines give you a working logger.
2. [CORE] A file handler as well as the stream handler, so there is a
   record after the terminal is closed.
3. [SECONDARY] Selectable levels (`resolve_level`, environment variables),
   so the amount of detail can change without editing code.
4. [SECONDARY] Rotation (`RotatingFileHandler`) and a dated file name
   (`default_log_file`), so the log file cannot grow without limit.
5. [ERRORS] Do not crash if the log file cannot be opened.
6. [SAFETY] Hide secrets (`redact`, `RedactingFormatter`,
   `register_secret`). Add this before the app handles any password or
   token, because log files are easy to share by accident.
"""

# `logging` is Python's built-in logging library.
import logging

# `os` gives access to environment variables (`os.environ`).
import os

# `re` is the regular-expression module, used here to find secrets.
import re

from datetime import datetime

# A file handler that starts a new file when the old one gets too big.
from logging.handlers import RotatingFileHandler

# `Path` handles file paths in a way that works on Windows, macOS and Linux.
from pathlib import Path

# [SECONDARY] Level 3: the allowed level names and the defaults.
VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
# The terminal shows INFO and above: enough to follow what the app is doing.
DEFAULT_STREAM_LEVEL = "INFO"
# The file records everything, so there is detail to read after a problem.
DEFAULT_FILE_LEVEL = "DEBUG"

# [SECONDARY] Level 4: where the log files go and how big they may get.
# `Path.home()` is the user's home folder; `/` joins path parts.
DEFAULT_LOG_DIR = Path.home() / ".my_app"
LOG_FILE_PREFIX = "my_app_"
# At about 500 KB the file is closed and a new one started.
MAX_BYTES = 500_000
# Keep this many old files; older ones are deleted automatically.
BACKUP_COUNT = 5

# [CORE] Level 1: the one shared logger. Every other file does
# `from my_app.logger import logger`, so all messages share its settings.
# `getLogger` with the same name always returns the same object.
logger = logging.getLogger("my_app")

# [SAFETY] Level 6: what a hidden secret is replaced with.
REDACTED = "[REDACTED]"

# [SAFETY] Level 6: the patterns that find secret-looking text.
# Each pair is (what to look for, what to put back). \1 keeps the text in
# the first brackets, such as "password=", and hides only the value after it.
# `re.IGNORECASE` makes "Password" and "PASSWORD" match too.
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

# [SAFETY] Level 6: exact secret values registered at run time. A leading
# underscore means "internal to this file". A `set` holds each value once.
_secrets = set()


# [SAFETY] Level 6: patterns cannot recognise every format, so the app also
# tells the logger the exact secrets it has loaded.
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
    # Short values such as "a" would replace that letter everywhere in the
    # log, which would make every message unreadable.
    if value and len(str(value)) >= 4:
        _secrets.add(str(value))


# [SAFETY] Level 6: the function that does the hiding.
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


# [SAFETY] Level 6: plugs `redact` into the logging system. A Formatter (not
# a Filter) is used because the formatter also builds the traceback text,
# and a traceback can contain a secret too.
class RedactingFormatter(logging.Formatter):
    """Format log records, then hide any secrets in the finished text."""

    def format(self, record):
        """Return the formatted record with secrets hidden."""
        # `super().format(record)` runs the normal Formatter first. Then the
        # finished text, traceback included, is cleaned.
        return redact(super().format(record))


# [SECONDARY] Level 3: choose a level from an argument, a variable or the
# default, in that order of priority.
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
    # `a or b or c` gives the first value that is not empty or None.
    # `.strip().upper()` accepts " info " and "Info" as well as "INFO".
    value = (argument or os.environ.get(env_name) or default).strip().upper()
    # [ERRORS] Fail early with a message that lists the allowed values.
    if value not in VALID_LEVELS:
        raise ValueError(
            f"{env_name} must be one of {', '.join(VALID_LEVELS)}, "
            f"not '{value}'"
        )
    # logging.DEBUG, logging.INFO and so on are numbers: look up by name.
    return getattr(logging, value)


# [SECONDARY] Level 4: a dated file name, so each run does not need its own
# invented name.
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
    # `now` is a parameter so a test can pass a fixed time and get a
    # predictable name.
    now = now or datetime.now()
    # Hyphens, not colons, because Windows file names cannot contain ":".
    return DEFAULT_LOG_DIR / f"{LOG_FILE_PREFIX}{now:%Y-%m-%d_%H-%M-%S}.log"


# [CORE] Levels 1 and 2: connects everything. Call it once, when the app
# starts.
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
    # [SECONDARY] Work out the settings first, so a bad level name fails
    # before anything else is changed.
    stream_level = resolve_level(
        stream_level, "MY_APP_STREAM_LOG_LEVEL", DEFAULT_STREAM_LEVEL
    )
    file_level = resolve_level(
        file_level, "MY_APP_FILE_LOG_LEVEL", DEFAULT_FILE_LEVEL
    )
    chosen_file = log_file or os.environ.get("MY_APP_LOG_FILE")
    log_path = Path(chosen_file) if chosen_file else default_log_file()

    # [CORE] Let every message reach the handlers.
    # Each handler then applies its own level.
    logger.setLevel(logging.DEBUG)

    # [CORE] Remove handlers from an earlier call so messages are not logged
    # twice. (Tests and a reloading server both call this more than once.)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    # [SAFETY] The formatter decides what each line looks like AND hides
    # secrets. %(asctime)s is the time, %(levelname)s the level and
    # %(message)s the text.
    formatter = RedactingFormatter("%(asctime)s - %(levelname)s - %(message)s")

    # [CORE] Level 1: the terminal handler. A handler is a destination.
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(stream_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # [ERRORS] A problem with the log file should not stop the app from
    # starting. Create the folder, then open the file.
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # [SECONDARY] Level 4: rotation. When the file reaches `maxBytes` it
        # is renamed to ".1", ".2" and so on, and a new file is started.
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
    # [CORE] Level 2: the file handler, set up the same way as the terminal
    # one.
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
