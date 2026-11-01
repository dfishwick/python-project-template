"""Tests for the example module."""

import pytest

from my_app.modules.example import clean_query


def test_clean_query_removes_spaces_at_both_ends():
    """Return the text without leading or trailing spaces."""
    assert clean_query("  hello  ") == "hello"


@pytest.mark.parametrize("text", ["", "   ", None])
def test_clean_query_rejects_empty_input(text):
    """Raise ValueError for empty, blank or missing text."""
    with pytest.raises(ValueError, match="must not be empty"):
        clean_query(text)
