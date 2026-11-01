"""Tests for the Flask routes.

A route test does not start a real server. Flask's `test_client()` sends
a pretend browser request straight into the app and gives back the reply,
so these tests are fast and need no network.

WHAT TO TEST FIRST (importance ranking)
---------------------------------------
1. [CORE] The home page loads (status 200). If this fails, nothing works.
2. [CORE] A normal search shows the expected result.
3. [ERRORS] Bad input (empty, field missing) shows an error message and
   is logged as a warning.
4. [ERRORS] An unexpected crash gives a plain 500 page and is logged, and
   an ordinary 404 is NOT treated as a crash.
"""

import logging

import pytest

from my_app.main import create_app


# A fixture is set-up code that pytest runs for you. Any test with a
# parameter named `client` receives the value this function returns. A new
# app per test means no test can affect another.
@pytest.fixture
def client():
    """Return a test client for a new app."""
    return create_app().test_client()


# Home page
# [CORE] Level 1.
def test_home_page_loads(client):
    """Return the search page with status 200."""
    response = client.get("/")
    assert response.status_code == 200


# Search
# [CORE] Level 2: the cleaned query (spaces removed) appears on the page.
def test_search_shows_the_query(client):
    """Show the cleaned query on the page."""
    response = client.post("/search", data={"query": "  hello "})
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "You searched for: hello" in page


# [ERRORS] Level 3. `caplog` is a built-in fixture that captures log
# messages, so a test can check that the right warning was written.
def test_empty_search_shows_an_error_and_warns(client, caplog):
    """Show an error and log a warning when the search box is empty."""
    response = client.post("/search", data={"query": ""})
    page = response.get_data(as_text=True)
    assert "Error: No input provided" in page
    assert any(
        record.levelname == "WARNING" and "No input" in record.getMessage()
        for record in caplog.records
    )


# [ERRORS] Level 3: the field is absent altogether, which is not the same
# as an empty box. Browsers cannot cause it, but other programs can.
def test_missing_form_field_is_treated_as_empty(client):
    """Show the empty-search error when the form has no query field."""
    response = client.post("/search", data={})
    assert "Error: No input provided" in response.get_data(as_text=True)


# Errors
def test_unexpected_error_returns_500_and_is_logged(
    client, monkeypatch, caplog
):
    """Show a plain error page and log the error with its traceback."""

    # A stand-in for the real function that always fails, to force the
    # "unexpected error" path. It accepts any arguments (`*args`).
    def broken_clean_query(*args):
        raise RuntimeError("test failure")

    # `monkeypatch` swaps the real function for the broken one for this test
    # only, and puts the real one back afterwards. The name is looked up in
    # `my_app.main`, the module that USES it, not `my_app.modules.example`.
    monkeypatch.setattr("my_app.main.clean_query", broken_clean_query)
    response = client.post("/search", data={"query": "anything"})
    page = response.get_data(as_text=True)
    assert response.status_code == 500
    assert "Something went wrong" in page
    # [ERRORS] Level 4: users must not see internal details, but the log must.
    assert "test failure" not in page
    assert "test failure" in caplog.text


# [ERRORS] Level 4: without the `HTTPException` check in main.py, every
# 404 would be logged as a crash and returned as a 500.
def test_unknown_page_is_404_and_not_logged_as_an_error(client, caplog):
    """Treat a missing page as normal, not as an unexpected error."""
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
