"""Shared pytest setup for all tests."""

import pytest

from my_app.logger import logger


@pytest.fixture(autouse=True)
def log_file_in_tmp_path(tmp_path, monkeypatch):
    """Send the log file to a temporary folder for every test.

    This stops the tests writing to the real log file in the user's
    home folder. Afterwards the handlers are removed and closed so the
    temporary log file is not left open.
    """
    monkeypatch.setenv("MY_APP_LOG_FILE", str(tmp_path / "logs" / "test.log"))
    yield
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
