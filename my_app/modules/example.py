"""Example module: replace it with the real logic of the project.

Keep logic like this in plain functions that know nothing about Flask, so
that it can be tested without starting a web server.

WHAT TO BUILD FIRST (importance ranking)
----------------------------------------
1. [CORE] Plain functions that take values in and give values back, with
   no Flask, no files and no network. These are the easiest code to test
   and the first thing to get right.
2. [ERRORS] Reject bad input early with a clear error (`ValueError` for a
   bad value, `TypeError` for a wrong type), and say so in the docstring
   under "Raises".
3. [EXAMPLE] `clean_query` itself is the pretend logic. Replace it, but
   keep the shape: validate, do the work, return a plain value.
"""


# [EXAMPLE] Replace the name, the work and the rule. Keep the pattern.
def clean_query(text):
    """Tidy a search query and reject an empty one.

    Parameters
    ----------
    text : str or None
        The text typed by the user. None is treated as empty.

    Returns
    -------
    str
        The text with spaces removed from both ends.

    Raises
    ------
    ValueError
        When the text is empty or only spaces.
    """
    # [CORE] `(text or "")` turns None into an empty string, so `.strip()`
    # never fails on a missing value. `.strip()` removes spaces, tabs and
    # newlines from both ends.
    cleaned = (text or "").strip()
    # [ERRORS] An empty string is "falsy", so `not cleaned` is True for
    # both "" and text that was only spaces.
    if not cleaned:
        raise ValueError("Query must not be empty")
    return cleaned
