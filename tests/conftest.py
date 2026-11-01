"""Shared pytest setup for all tests.

pytest finds this file automatically. Anything defined here is available
to every test file in the folder, with no import.

[CORE] Build this when the first test would otherwise touch something real
(here, the user's log folder). Isolating tests from the real machine is
what makes them safe to run anywhere, including on GitHub's servers.
"""

import pytest

from my_app.logger import logger


# `autouse=True`: runs around EVERY test without being asked for.
@pytest.fixture(autouse=True)
def log_file_in_tmp_path(tmp_path, monkeypatch):
    """Send the log file to a temporary folder for every test.

    This stops the tests writing to the real log file in the user's
    home folder. Afterwards the handlers are removed and closed so the
    temporary log file is not left open.
    """
    # Point the log file at a temporary folder (`tmp_path` is unique to each
    # test and deleted afterwards).
    monkeypatch.setenv("MY_APP_LOG_FILE", str(tmp_path / "logs" / "test.log"))
    # Everything above `yield` is set-up (before the test). Everything below
    # is tear-down (after the test), and runs even if the test failed.
    yield
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
