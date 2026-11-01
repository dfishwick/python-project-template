"""Tests for loading credentials from outside the repository."""

import pytest

import my_app.config as config
import my_app.logger as log_module
from my_app.config import ConfigError, load_credentials
from my_app.logger import logger, redact, setup_logging

FILE_TEXT = "[api]\nemail = alice@example.org\npassword = hunter2-file\n"


def write_file(tmp_path, text):
    """Write `text` to a credentials file and return its path."""
    path = tmp_path / "credentials.ini"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Clear credential variables and registered secrets."""
    monkeypatch.delenv(config.EMAIL_VAR, raising=False)
    monkeypatch.delenv(config.PASSWORD_VAR, raising=False)
    monkeypatch.setattr(log_module, "_secrets", set())


@pytest.fixture
def credentials_file(tmp_path):
    """Write a valid credentials file and return its path."""
    return write_file(tmp_path, FILE_TEXT)


# Where the values come from
def test_credentials_are_read_from_the_file(credentials_file):
    """Return the email and password written in the file."""
    email, password = load_credentials(credentials_file)
    assert email == "alice@example.org"
    assert password == "hunter2-file"


def test_environment_variable_beats_the_file(credentials_file, monkeypatch):
    """Use an environment variable in place of the file's value."""
    monkeypatch.setenv(config.PASSWORD_VAR, "hunter2-env")
    email, password = load_credentials(credentials_file)
    assert email == "alice@example.org"
    assert password == "hunter2-env"


def test_environment_variables_alone_are_enough(tmp_path, monkeypatch):
    """Work without any file, as in Docker or CI."""
    monkeypatch.setenv(config.EMAIL_VAR, "bob@example.org")
    monkeypatch.setenv(config.PASSWORD_VAR, "hunter2-env")
    result = load_credentials(tmp_path / "none.ini")
    assert result == ("bob@example.org", "hunter2-env")


def test_default_file_location_is_used(credentials_file, monkeypatch):
    """Read the default file when no path is given."""
    monkeypatch.setattr(config, "CREDENTIALS_FILE", credentials_file)
    assert load_credentials()[0] == "alice@example.org"


# Missing or broken input
def test_missing_credentials_name_both_variables(tmp_path):
    """Say which settings are missing when there is no file or variable."""
    with pytest.raises(ConfigError) as error:
        load_credentials(tmp_path / "none.ini")
    assert config.EMAIL_VAR in str(error.value)
    assert config.PASSWORD_VAR in str(error.value)


def test_only_the_missing_value_is_named(tmp_path):
    """Name just the setting that is missing."""
    path = write_file(tmp_path, "[api]\nemail = alice@example.org\n")
    with pytest.raises(ConfigError, match=r"Missing MY_APP_API_PASSWORD\."):
        load_credentials(path)


def test_empty_values_count_as_missing(tmp_path):
    """Treat blank settings in the file as not set."""
    path = write_file(tmp_path, "[api]\nemail =\npassword =\n")
    with pytest.raises(ConfigError, match="Missing"):
        load_credentials(path)


def test_file_without_the_api_section_counts_as_missing(tmp_path):
    """Ignore a file that has no [api] section."""
    path = write_file(tmp_path, "[other]\nemail = alice@example.org\n")
    with pytest.raises(ConfigError, match="Missing"):
        load_credentials(path)


def test_unparsable_file_does_not_quote_its_lines(tmp_path):
    """Keep the file's text out of the error, in case it is the password."""
    path = write_file(tmp_path, "password hunter2\n")
    with pytest.raises(ConfigError) as error:
        load_credentials(path)
    assert "hunter2" not in str(error.value)
    assert error.value.__suppress_context__ is True


# Keeping the password out of the logs
def test_loaded_password_is_registered_as_a_secret(credentials_file):
    """Hide the loaded password anywhere it appears in a log."""
    load_credentials(credentials_file)
    assert "hunter2-file" not in redact("login with hunter2-file failed")


def test_loading_credentials_logs_no_values(tmp_path, credentials_file):
    """Log that credentials were loaded, without the email or password."""
    log_file = tmp_path / "app.log"
    setup_logging(log_file=log_file)
    load_credentials(credentials_file)
    text = log_file.read_text(encoding="utf-8")
    assert "Loaded API credentials" in text
    assert "alice@example.org" not in text
    assert "hunter2-file" not in text


def test_error_traceback_does_not_leak_the_file_text(tmp_path):
    """Keep the password out of a logged traceback for a bad file."""
    log_file = tmp_path / "app.log"
    setup_logging(log_file=log_file)
    path = write_file(tmp_path, "password hunter2\n")
    try:
        load_credentials(path)
    except ConfigError:
        logger.exception("Could not load credentials")
    text = log_file.read_text(encoding="utf-8")
    assert "Traceback" in text
    assert "hunter2" not in text
