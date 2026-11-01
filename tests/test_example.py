"""Tests for the example module.

WHAT TO TEST FIRST (importance ranking)
---------------------------------------
1. [CORE] One test of normal use: good input gives the expected output.
2. [ERRORS] One test for each way the function can fail, with the exact
   inputs that trigger it (here: empty, only spaces, and None).
Pure functions like this are the easiest tests to write, so start here.
"""

import pytest

from my_app.modules.example import clean_query


# [CORE] Level 1: normal use. `assert` fails the test if the condition is
# False. Test names say what should happen, so a failure reads like a
# sentence.
def test_clean_query_removes_spaces_at_both_ends():
    """Return the text without leading or trailing spaces."""
    assert clean_query("  hello  ") == "hello"


# [ERRORS] Level 2: `parametrize` runs the same test once for each value in
# the list, so three inputs need only one test function. `pytest.raises`
# passes only if the code raises that error, and `match` also checks that
# the message contains the given text.
@pytest.mark.parametrize("text", ["", "   ", None])
def test_clean_query_rejects_empty_input(text):
    """Raise ValueError for empty, blank or missing text."""
    with pytest.raises(ValueError, match="must not be empty"):
        clean_query(text)
