# Technical guide

## Layout

```
my_app/
    main.py          the Flask app factory and routes
    logger.py        logging set-up and hiding of secrets
    config.py        loads credentials from outside the repository
    client.py        the only file that makes web (API) requests
    modules/         plain Python logic, with no dependence on Flask
    templates/       HTML pages
    static/          style sheet
tests/               pytest tests, at the project root
docs/                these pages, built with MkDocs
```

## How a request is handled

1. `create_app` in `main.py` sets up logging and registers the routes.
2. A route reads the request and calls a function in `modules/`.
3. The function returns a result or raises an error.
4. The route renders `index.html`, or logs the problem and shows an error.
5. Any error nobody expected goes to `handle_unexpected_error`, which logs
   the traceback and shows a plain error page.

## Design decisions

- **The app is built inside `create_app`.** Tests can then make their own
  copy instead of sharing one created at import time.
- **Logic lives in `modules/`, not in the routes.** A plain function can be
  tested without a web server.
- **Logging is set up once, in `create_app`.** Every other file imports the
  shared `logger`.
- **Credentials stay outside the repository.** See
  [Credentials](credentials.md).
- **Versions are pinned.** `pyproject.toml` fixes the exact version of each
  package so the app builds the same way everywhere.

## Reading the code: importance tags

Every code and configuration file begins with a "what to build first"
ranking, and each element carries a tag in a comment. Search for a tag to
find all the elements of that level.

| Tag | Meaning |
|---|---|
| `[CORE]` | The smallest working version. Build and test this first. |
| `[ERRORS]` | Turns failures into clear messages. Build second. |
| `[SAFETY]` | Protects input, secrets and credentials. Add before real data or users. |
| `[SECONDARY]` | Useful, but the app works without it. Add as needed. |
| `[EXAMPLE]` | Pretend content. Replace it with the real project. |

## Calling a web API

All network calls live in `my_app/client.py`.

- `ApiClient.get_json(path, params)` sends a GET request and returns the
  JSON reply. It always sets a timeout, checks the HTTP status, and turns
  every failure into a single `ApiError`.
- `validate_item_id` checks an ID before any request is made, so bad input
  costs no network traffic and cannot change the web address.
- Credentials come from `my_app.config.load_credentials()` and are passed
  as `ApiClient(auth=...)`. They are never written in code or logged.
- Tests replace `requests.get` with a fake, so they need no network. See
  `tests/test_client.py` for the pattern.

To use a real API, change `EXAMPLE_BASE_URL`, the endpoint in `lookup`, and
the ID rule in `ITEM_ID_PATTERN`.

## Adding a feature

1. Write the logic as a function in a new file in `modules/`, with a
   docstring in the NumPy style.
2. Add tests for it in `tests/`, including the error cases.
3. Call it from a route in `main.py`.
4. Add a route test in `tests/test_routes.py`.
5. Update the [user guide](user-guide.md) if the behaviour changes.

## Style

- PEP 8, with lines of at most 79 characters.
- NumPy-style docstrings on every module, function and class.
- Comments explain why, not what.
