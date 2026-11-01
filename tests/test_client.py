"""Tests for my_app.client.

None of these tests touch the network. `requests.get` is replaced with a
fake (a "stub") using pytest's `monkeypatch`, so the tests are:

* fast: no waiting for a server;
* reliable: they do not fail because the API is down or you are offline;
* able to test failures (timeouts, 500 errors, bad JSON) that a real
  server will not produce on demand.

How a fake works, in three steps:
1. Write a small class or function that looks like the real thing.
2. Use `monkeypatch.setattr("my_app.client.requests.get", fake)` so the
   code under test calls the fake instead. `monkeypatch` undoes this
   automatically when the test ends.
3. Check what the code did with the fake's answer.
"""

import logging

import pytest
import requests

from my_app.client import (
    ApiClient,
    ApiError,
    InvalidItemIdError,
    validate_item_id,
)


class FakeResponse:
    """A stand-in for the object `requests.get` returns.

    Only the two methods the client uses are provided: `raise_for_status`
    and `json`. Add more if your client starts using more.
    """

    def __init__(self, data=None, status_code=200, json_error=False):
        # Store what the test wants the pretend server to say.
        self.data = data
        self.status_code = status_code
        self.json_error = json_error

    def raise_for_status(self):
        """Raise an HTTPError for 4xx and 5xx codes, as the real one does."""
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(
                f"{self.status_code} Error for url"
            )

    def json(self):
        """Return the data, or fail like a reply that is not valid JSON."""
        if self.json_error:
            raise ValueError("No JSON object could be decoded")
        return self.data


def fake_get(response=None, error=None, calls=None):
    """Build a replacement for `requests.get`.

    Parameters
    ----------
    response : FakeResponse, optional
        What the pretend server replies with.
    error : Exception, optional
        If given, raise this instead of replying (a network failure).
    calls : list, optional
        Each call is appended here as (url, keyword arguments), so a test
        can check exactly what the client sent.
    """

    def _get(url, **kwargs):
        # `**kwargs` collects params=, auth= and timeout= into a dict.
        if calls is not None:
            calls.append((url, kwargs))
        if error is not None:
            raise error
        return response

    return _get


@pytest.fixture
def client():
    """Return a client pointed at a made-up address."""
    return ApiClient(base_url="https://api.test/", timeout=5)


# validate_item_id
@pytest.mark.parametrize(
    "item_id", ["ABC123", "NM_000088.3", "HGNC:5", "a", "x" * 50, "a-b_c.d"]
)
def test_valid_ids_are_accepted(item_id):
    """Return the ID unchanged when it has the expected format."""
    assert validate_item_id(item_id) == item_id


@pytest.mark.parametrize(
    "item_id",
    [
        "",  # empty
        "x" * 51,  # one character too long
        "has space",
        "a/b",  # would change the web address
        "a?b=1",  # would add a query string
        "abc\n",  # trailing newline: `fullmatch` must reject it
        None,  # not text at all
        123,
    ],
)
def test_invalid_ids_are_rejected(item_id):
    """Raise InvalidItemIdError for anything outside the allowed shape."""
    with pytest.raises(InvalidItemIdError):
        validate_item_id(item_id)


def test_long_invalid_id_is_shortened_in_the_message():
    """Keep a huge bad value from flooding the error message."""
    with pytest.raises(InvalidItemIdError) as error:
        validate_item_id("x" * 5000 + " ")
    assert len(str(error.value)) < 200


# build_url
@pytest.mark.parametrize(
    "base_url", ["https://api.test", "https://api.test/", "https://api.test//"]
)
@pytest.mark.parametrize("path", ["items/1", "/items/1"])
def test_build_url_joins_with_exactly_one_slash(base_url, path):
    """Give the same address however the slashes are written."""
    assert ApiClient(base_url=base_url).build_url(path) == (
        "https://api.test/items/1"
    )


# get_json
def test_get_json_returns_data_and_sends_the_right_arguments(
    client, monkeypatch
):
    """Return the parsed JSON and pass url, params, auth and timeout on."""
    calls = []
    reply = FakeResponse(data={"name": "demo"})
    monkeypatch.setattr(
        "my_app.client.requests.get", fake_get(response=reply, calls=calls)
    )
    client.auth = ("user", "pass")
    result = client.get_json("items/1", params={"build": "GRCh38"})
    assert result == {"name": "demo"}
    url, kwargs = calls[0]
    assert url == "https://api.test/items/1"
    assert kwargs == {
        "params": {"build": "GRCh38"},
        "auth": ("user", "pass"),
        "timeout": 5,
    }


def test_timeout_becomes_api_error(client, monkeypatch):
    """Turn a requests Timeout into ApiError and keep the cause."""
    monkeypatch.setattr(
        "my_app.client.requests.get",
        fake_get(error=requests.exceptions.Timeout("too slow")),
    )
    with pytest.raises(ApiError, match="did not reply within 5 seconds") as e:
        client.get_json("items/1")
    # `__cause__` is the original error that `raise ... from error` kept.
    assert isinstance(e.value.__cause__, requests.exceptions.Timeout)


def test_connection_error_becomes_api_error(client, monkeypatch):
    """Turn a connection failure into ApiError."""
    monkeypatch.setattr(
        "my_app.client.requests.get",
        fake_get(error=requests.exceptions.ConnectionError("no route")),
    )
    with pytest.raises(ApiError, match="request to the API failed"):
        client.get_json("items/1")


@pytest.mark.parametrize("status_code", [400, 404, 500, 503])
def test_http_error_status_becomes_api_error(client, monkeypatch, status_code):
    """Treat 4xx and 5xx replies as failures, not as data."""
    reply = FakeResponse(status_code=status_code)
    monkeypatch.setattr("my_app.client.requests.get", fake_get(response=reply))
    with pytest.raises(ApiError):
        client.get_json("items/1")


def test_invalid_json_becomes_api_error(client, monkeypatch):
    """Turn an unreadable reply (such as an HTML page) into ApiError."""
    reply = FakeResponse(json_error=True)
    monkeypatch.setattr("my_app.client.requests.get", fake_get(response=reply))
    with pytest.raises(ApiError, match="not valid JSON"):
        client.get_json("items/1")


def test_query_string_is_not_written_to_the_log(client, monkeypatch, caplog):
    """Keep query values (which may hold tokens) out of the log."""
    reply = FakeResponse(data={})
    monkeypatch.setattr("my_app.client.requests.get", fake_get(response=reply))
    # The logger's level is set by setup_logging, which has not run in this
    # test, so ask caplog to capture DEBUG messages from our logger.
    caplog.set_level(logging.DEBUG, logger="my_app")
    client.get_json("items/1", params={"token": "s3cretvalue"})
    assert "GET https://api.test/items/1" in caplog.text
    assert "s3cretvalue" not in caplog.text


# lookup
def test_lookup_requests_the_quoted_item_path(client, monkeypatch):
    """Encode the ID in the address ("HGNC:5" becomes "HGNC%3A5")."""
    calls = []
    reply = FakeResponse(data={"id": "HGNC:5"})
    monkeypatch.setattr(
        "my_app.client.requests.get", fake_get(response=reply, calls=calls)
    )
    assert client.lookup("HGNC:5") == {"id": "HGNC:5"}
    assert calls[0][0] == "https://api.test/items/HGNC%3A5"


def test_lookup_rejects_a_bad_id_without_calling_the_api(client, monkeypatch):
    """Raise before any request, so a typo costs no network traffic."""
    calls = []
    monkeypatch.setattr(
        "my_app.client.requests.get",
        fake_get(response=FakeResponse(), calls=calls),
    )
    with pytest.raises(InvalidItemIdError):
        client.lookup("../secret")
    # No request was made.
    assert calls == []
