"""Tests for the logging setup.

Logging is hard to test by eye, because a wrong level or a duplicated
handler looks fine on screen. These tests check each setting directly.

WHAT TO TEST FIRST (importance ranking)
---------------------------------------
1. [CORE] The right handlers exist, and calling setup twice does not
   duplicate them (duplicates print every message twice).
2. [SECONDARY] Levels: defaults, arguments, environment variables, which
   wins, and that an invalid name is rejected.
3. [CORE] Messages really reach the file and the terminal, and respect
   each level.
4. [SECONDARY] The dated file name and rotation.
5. [ERRORS] A log file that cannot be opened does not stop the app.
"""

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

import pytest

import my_app.logger as log_module
from my_app.logger import (
    logger,
    setup_logging,
    resolve_level,
    default_log_file,
)


# Runs before every test: removes any level variables set on your own
# computer, so a test only sees what it sets itself.
@pytest.fixture(autouse=True)
def clear_log_settings(monkeypatch):
    """Remove the level variables so only each test's own settings count."""
    for name in ("MY_APP_STREAM_LOG_LEVEL", "MY_APP_FILE_LOG_LEVEL"):
        monkeypatch.delenv(name, raising=False)


# Two small helper functions, not tests. They keep the tests below short.
def stream_handlers():
    """Return the logger's stream handlers, not including the file handler."""
    # RotatingFileHandler is a kind of StreamHandler, so check the exact type.
    return [h for h in logger.handlers if type(h) is logging.StreamHandler]


def file_handlers():
    """Return the logger's rotating file handlers."""
    return [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]


# [CORE] Level 1.
# Handlers
def test_setup_adds_one_stream_and_one_rotating_file_handler():
    """Log to the stream and to a rotating file."""
    setup_logging()
    assert len(stream_handlers()) == 1
    assert len(file_handlers()) == 1


def test_calling_setup_twice_does_not_duplicate_handlers():
    """Replace the handlers instead of adding more."""
    setup_logging()
    setup_logging()
    assert len(stream_handlers()) == 1
    assert len(file_handlers()) == 1


# [SECONDARY] Level 2. The order of priority is: argument, then environment
# variable, then default.
# Levels
def test_default_levels():
    """Use INFO for the stream and DEBUG for the file."""
    setup_logging()
    assert stream_handlers()[0].level == logging.INFO
    assert file_handlers()[0].level == logging.DEBUG


def test_levels_from_arguments_ignore_case():
    """Accept level names in any case."""
    setup_logging(stream_level="error", file_level="Warning")
    assert stream_handlers()[0].level == logging.ERROR
    assert file_handlers()[0].level == logging.WARNING


def test_levels_from_environment_variables(monkeypatch):
    """Read both levels from environment variables."""
    monkeypatch.setenv("MY_APP_STREAM_LOG_LEVEL", "CRITICAL")
    monkeypatch.setenv("MY_APP_FILE_LOG_LEVEL", "INFO")
    setup_logging()
    assert stream_handlers()[0].level == logging.CRITICAL
    assert file_handlers()[0].level == logging.INFO


def test_argument_beats_environment_variable(monkeypatch):
    """Use the argument when both an argument and a variable are given."""
    monkeypatch.setenv("MY_APP_STREAM_LOG_LEVEL", "CRITICAL")
    setup_logging(stream_level="DEBUG")
    assert stream_handlers()[0].level == logging.DEBUG


def test_empty_environment_variable_uses_default(monkeypatch):
    """Treat an empty variable as not set."""
    monkeypatch.setenv("MY_APP_STREAM_LOG_LEVEL", "")
    level = resolve_level(None, "MY_APP_STREAM_LOG_LEVEL", "INFO")
    assert level == logging.INFO


def test_invalid_level_raises_value_error():
    """Reject a level name that does not exist."""
    with pytest.raises(ValueError, match="MY_APP_STREAM_LOG_LEVEL"):
        setup_logging(stream_level="LOUD")


# [CORE] Level 3: write a message and read it back, which proves the whole
# chain of logger, handler, level and file is connected.
# Messages go where they should
def test_file_only_receives_messages_at_or_above_its_level(tmp_path):
    """Leave messages below the file level out of the file."""
    log_file = tmp_path / "level.log"
    setup_logging(file_level="WARNING", log_file=log_file)
    logger.info("info text")
    logger.warning("warning text")
    text = log_file.read_text(encoding="utf-8")
    assert "warning text" in text
    assert "info text" not in text


# `capsys` captures terminal output. Logging goes to stderr, hence `.err`.
def test_stream_only_shows_messages_at_or_above_its_level(tmp_path, capsys):
    """Leave messages below the stream level off the terminal."""
    setup_logging(stream_level="WARNING", log_file=tmp_path / "s.log")
    logger.info("quiet text")
    logger.warning("loud text")
    shown = capsys.readouterr().err
    assert "loud text" in shown
    assert "quiet text" not in shown


def test_missing_log_folder_is_created(tmp_path):
    """Create the log folder and its parents when they do not exist."""
    log_file = tmp_path / "a" / "b" / "app.log"
    setup_logging(log_file=log_file)
    logger.info("hello")
    assert log_file.exists()


# [SECONDARY] Level 4. The tests point `DEFAULT_LOG_DIR` at a temporary
# folder so they never touch your real log folder.
# Default log file name
def test_default_log_file_name_has_date_and_time(tmp_path, monkeypatch):
    """Name a new log file with the date and time it is made."""
    monkeypatch.setattr(log_module, "DEFAULT_LOG_DIR", tmp_path)
    path = default_log_file(datetime(2026, 11, 1, 4, 25, 0))
    assert path == tmp_path / "my_app_2026-11-01_04-25-00.log"


def test_default_log_file_reuses_the_newest_existing_file(
    tmp_path, monkeypatch
):
    """Keep using the existing file instead of making a new one."""
    monkeypatch.setattr(log_module, "DEFAULT_LOG_DIR", tmp_path)
    older = tmp_path / "my_app_2026-01-01_00-00-00.log"
    newest = tmp_path / "my_app_2026-06-01_00-00-00.log"
    older.write_text("older", encoding="utf-8")
    newest.write_text("newest", encoding="utf-8")
    assert default_log_file() == newest


def test_default_log_file_is_one_file_across_start_ups(tmp_path, monkeypatch):
    """Use one dated file in the default folder across start-ups."""
    monkeypatch.delenv("MY_APP_LOG_FILE")
    monkeypatch.setattr(log_module, "DEFAULT_LOG_DIR", tmp_path)
    setup_logging()
    logger.info("first start")
    setup_logging()
    logger.info("second start")
    files = list(tmp_path.glob("my_app_*.log"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert "first start" in text
    assert "second start" in text


# [SECONDARY] Level 4. The limits are made tiny (200 bytes) so that 50
# short messages are enough to trigger rotation.
# Rotation
def test_log_file_rotates_and_keeps_limited_backups(tmp_path, monkeypatch):
    """Start a new file when the limit is reached and keep few old files."""
    monkeypatch.setattr(log_module, "MAX_BYTES", 200)
    monkeypatch.setattr(log_module, "BACKUP_COUNT", 2)
    log_file = tmp_path / "rotate.log"
    setup_logging(log_file=log_file)
    for number in range(50):
        logger.info(f"message number {number}")
    assert (tmp_path / "rotate.log.1").exists()
    assert (tmp_path / "rotate.log.2").exists()
    assert not (tmp_path / "rotate.log.3").exists()
    assert log_file.stat().st_size <= 200
    # Old files are renamed, not compressed, so they are still plain text.
    assert "message number" in (tmp_path / "rotate.log.1").read_text(
        encoding="utf-8"
    )


# [ERRORS] Level 5. A file cannot be created inside another FILE, so using
# an ordinary file as the "folder" is a simple way to force an OSError.
# Problems with the log file
def test_unusable_log_path_falls_back_to_stream_only(tmp_path, caplog):
    """Keep running with the stream only when the file cannot be opened."""
    blocker = tmp_path / "blocker"
    blocker.write_text("this is a file, not a folder", encoding="utf-8")
    setup_logging(log_file=blocker / "app.log")
    assert len(file_handlers()) == 0
    assert len(stream_handlers()) == 1
    assert "Could not open log file" in caplog.text
