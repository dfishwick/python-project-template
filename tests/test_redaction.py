"""Tests that secrets are hidden in log output."""

import pytest

import my_app.logger as log_module
from my_app.logger import (
    REDACTED,
    logger,
    redact,
    register_secret,
    setup_logging,
)


@pytest.fixture(autouse=True)
def no_registered_secrets(monkeypatch):
    """Start every test with no registered secrets."""
    monkeypatch.setattr(log_module, "_secrets", set())


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
def test_redact_leaves_ordinary_text_alone(text):
    """Do not change log text that holds no secret."""
    assert redact(text) == text


# Registered secrets
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


def test_longest_registered_secret_is_hidden_first():
    """Hide a secret whole when another secret is part of it."""
    register_secret("hunter2")
    register_secret("hunter2-extra")
    assert redact("x hunter2-extra y") == f"x {REDACTED} y"


# Through the real handlers
def test_secret_is_hidden_in_the_log_file(tmp_path):
    """Write the masked text to the log file."""
    log_file = tmp_path / "secret.log"
    setup_logging(log_file=log_file)
    logger.info("login with password=hunter2")
    text = log_file.read_text(encoding="utf-8")
    assert "hunter2" not in text
    assert "password=" in text


def test_secret_is_hidden_on_the_stream(tmp_path, capsys):
    """Show the masked text on the terminal."""
    setup_logging(log_file=tmp_path / "secret.log")
    logger.warning("token=hunter2")
    output = capsys.readouterr().err
    assert "hunter2" not in output
    assert REDACTED in output


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
