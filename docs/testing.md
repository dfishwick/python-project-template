# Testing

The tests are in the `tests` folder at the root of the project, not inside
the package. They use pytest.

## Run the tests

```
python -m pytest
```

## Coverage

```
python -m pytest --cov=my_app --cov-report=term-missing --cov-report=html
```

`--cov=my_app` measures only the app code, not the tests. `term-missing`
lists the line numbers that no test reached. `html` writes a report to
`htmlcov/index.html`.

## Style checks

```
python -m pip install flake8 black
flake8 my_app tests
black --check my_app tests
```

`flake8` prints nothing when the code follows PEP 8. The line length for
Black (79) is set in `pyproject.toml`.

## Continuous integration

GitHub Actions builds the container, starts it, runs the tests with
coverage and uploads the result to Codecov on every pull request. The
badges at the top of the README show the latest result.
