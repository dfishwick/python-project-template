"""Tests that secrets are hidden in log output.

All of these are [SAFETY] tests. Security code that is not tested tends to
fail quietly, so each way a secret could leak has its own test.

WHAT TO TEST FIRST (importance ranking)
---------------------------------------
1. [SAFETY] Each pattern hides its value (`test_redact_hides...`).
2. [SAFETY] Ordinary text is NOT changed. A rule that hides too much
   makes the log useless, so people switch it off.
3. [SAFETY] Exact secrets registered at run time are hidden.
4. [SAFETY] The real handlers (file, terminal, traceback) hide secrets.
   These prove the pieces are connected, not just correct on their own.
"""

import pytest

import my_app.logger as log_module
from my_app.logger import (
    REDACTED,
    logger,
    redact,
    register_secret,
    setup_logging,
)


# `autouse=True` runs this fixture for every test in the file without it
# being named. It replaces the module's secret set with an empty one, and
# `monkeypatch` restores the real set afterwards, so no test leaks into
# the next.
@pytest.fixture(autouse=True)
def no_registered_secrets(monkeypatch):
    """Start every test with no registered secrets."""
    monkeypatch.setattr(log_module, "_secrets", set())


# [SAFETY] Level 1. Each string below is one format a secret might take.
# The value is always "hunter2", an obviously fake password.
# Patterns
@pytest.mark.parametrize(
    "text",
    [
        "password=hunter2",
        "PASSWORD: hunter2",
        '{"password": "hunter2"}',
        "SHAIP_BEARER_TOKEN=hunter2",
        "api_key=hunter2&page=2",
        "Authorization: Bearer hunter2",
        "Authorization: Basic hunter2",
        "GET https://alice:hunter2@example.org/path",
    ],
)
def test_redact_hides_secret_like_values(text):
    """Hide the value after a password, token, key or login header."""
    result = redact(text)
    assert "hunter2" not in result
    assert REDACTED in result


@pytest.mark.parametrize(
    "text",
    [
        "Result found for sample",
        "Loaded 5 items from data/example.txt",
        "Counted 3 tokens: 5 unique",
    ],
)
# [SAFETY] Level 2: the opposite check. Note "Counted 3 tokens": the word
# "tokens" appears, but no value follows `=` or `:`, so nothing is hidden.
def test_redact_leaves_ordinary_text_alone(text):
    """Do not change log text that holds no secret."""
    assert redact(text) == text


# Registered secrets
# [SAFETY] Level 3. The text has no "password=" in it, so only the
# registered value can catch it.
def test_registered_secret_is_hidden_in_any_format():
    """Hide a registered value even where no pattern would catch it."""
    register_secret("s3cr3t-value")
    result = redact("odd format s3cr3t-value here")
    assert result == f"odd format {REDACTED} here"


@pytest.mark.parametrize("value", [None, "", "abc"])
def test_register_secret_ignores_empty_and_short_values(value):
    """Ignore values that would damage ordinary text if hidden."""
    register_secret(value)
    assert redact("abc is fine") == "abc is fine"


# [SAFETY] Level 3: if "hunter2" were replaced first, "-extra" would be
# left behind in the log.
def test_longest_registered_secret_is_hidden_first():
    """Hide a secret whole when another secret is part of it."""
    register_secret("hunter2")
    register_secret("hunter2-extra")
    assert redact("x hunter2-extra y") == f"x {REDACTED} y"


# Through the real handlers
# [SAFETY] Level 4. `tmp_path` is a built-in fixture giving each test its
# own empty temporary folder, so no real log file is touched.
def test_secret_is_hidden_in_the_log_file(tmp_path):
    """Write the masked text to the log file."""
    log_file = tmp_path / "secret.log"
    setup_logging(log_file=log_file)
    logger.info("login with password=hunter2")
    text = log_file.read_text(encoding="utf-8")
    assert "hunter2" not in text
    assert "password=" in text


# `capsys` captures what the program prints. Log messages from a
# StreamHandler go to stderr, so read `.err`.
def test_secret_is_hidden_on_the_stream(tmp_path, capsys):
    """Show the masked text on the terminal."""
    setup_logging(log_file=tmp_path / "secret.log")
    logger.warning("token=hunter2")
    output = capsys.readouterr().err
    assert "hunter2" not in output
    assert REDACTED in output


# [SAFETY] Level 4. This is the reason `RedactingFormatter` exists: a
# Filter would clean the message but miss the traceback text.
def test_secret_in_a_traceback_is_hidden(tmp_path):
    """Hide a secret that appears inside an exception traceback."""
    log_file = tmp_path / "secret.log"
    setup_logging(log_file=log_file)
    try:
        raise RuntimeError("failed: https://alice:hunter2@example.org/x")
    except RuntimeError:
        logger.exception("Request failed")
    text = log_file.read_text(encoding="utf-8")
    assert "Traceback" in text
    assert "hunter2" not in text
