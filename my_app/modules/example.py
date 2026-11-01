"""Example module: replace it with the real logic of the project.

Keep logic like this in plain functions that know nothing about Flask, so
that it can be tested without starting a web server.
"""


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
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Query must not be empty")
    return cleaned
