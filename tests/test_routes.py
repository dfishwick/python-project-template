"""Tests for the Flask routes."""

import logging

import pytest

from my_app.main import create_app


@pytest.fixture
def client():
    """Return a test client for a new app."""
    return create_app().test_client()


# Home page
def test_home_page_loads(client):
    """Return the search page with status 200."""
    response = client.get("/")
    assert response.status_code == 200


# Search
def test_search_shows_the_query(client):
    """Show the cleaned query on the page."""
    response = client.post("/search", data={"query": "  hello "})
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "You searched for: hello" in page


def test_empty_search_shows_an_error_and_warns(client, caplog):
    """Show an error and log a warning when the search box is empty."""
    response = client.post("/search", data={"query": ""})
    page = response.get_data(as_text=True)
    assert "Error: No input provided" in page
    assert any(
        record.levelname == "WARNING" and "No input" in record.getMessage()
        for record in caplog.records
    )


def test_missing_form_field_is_treated_as_empty(client):
    """Show the empty-search error when the form has no query field."""
    response = client.post("/search", data={})
    assert "Error: No input provided" in response.get_data(as_text=True)


# Errors
def test_unexpected_error_returns_500_and_is_logged(
    client, monkeypatch, caplog
):
    """Show a plain error page and log the error with its traceback."""

    def broken_clean_query(*args):
        raise RuntimeError("test failure")

    monkeypatch.setattr("my_app.main.clean_query", broken_clean_query)
    response = client.post("/search", data={"query": "anything"})
    page = response.get_data(as_text=True)
    assert response.status_code == 500
    assert "Something went wrong" in page
    assert "test failure" not in page
    assert "test failure" in caplog.text


def test_unknown_page_is_404_and_not_logged_as_an_error(client, caplog):
    """Treat a missing page as normal, not as an unexpected error."""
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
