# Using this template

Delete this file once the new project is set up.

## 1. Make the new repository

On GitHub, open this template repository and choose **Use this template**,
then **Create a new repository**. Give it its own name. Clone the new
repository to your computer.

## 2. Rename everything

In VS Code use **Edit, Replace in Files** (Ctrl+Shift+H) and replace each
of these in turn, checking the list of matches before you replace:

| Find | Replace with | Where it appears |
|---|---|---|
| `my_app` | the package name, lower case with underscores | code, tests, Dockerfile, workflows, docs |
| `my-app` | the name with hyphens | `environment.yml`, CI, docs |
| `MY_APP` | the name in capitals with underscores | settings names in `logger.py`, `config.py`, tests, docs |
| `My App` | the readable project name | README, docs, `mkdocs.yml`, the page template |
| `YOUR_USERNAME` | your GitHub user name | README, `mkdocs.yml`, docs |
| `YOUR_REPO` | the repository name | README, `mkdocs.yml`, docs |

Then rename the folder `my_app` to the package name. Do the folder last so
VS Code can still find the files while replacing.

Also check `ENV_PREFIX` and `APP_NAME`-style names in `my_app/logger.py`:
the log folder, the log file name and the three settings names (such as
`MY_APP_STREAM_LOG_LEVEL`) all come from the replacements above.

## 3. Check it works before changing anything else

```
conda env create -f environment.yml
conda activate my-app
python -m pip install -e .
python -m pytest
```

All tests should pass with the new names.

## 4. GitHub settings (once per repository)

- **Pages:** Settings, Pages, Source: GitHub Actions.
- **Codecov:** add the repository at codecov.io, copy its token, and save it
  under Settings, Secrets and variables, Actions as `CODECOV_TOKEN`.
- **Branch protection:** Settings, Branches, add a rule for `main` that
  requires a pull request and the CI check to pass.
- **Collaborators:** add your team, and the unit leads if the repository is
  private.

## 5. Working rules from the rubric

- Plan each piece of work in an issue (use the Sprint template), assign it,
  and name the branch after the issue number.
- Merge only through a pull request that another team member reviews.
- Write "Related to #NUMBER" in pull requests, never "Closes", and do not
  close issues or delete branches. The examiners need to see them.

## 6. Replace the example code

Start with the tags. Each file's opening comment ranks its parts, and
`[EXAMPLE]` marks what to replace. `[CORE]` is where to begin if you are
building a simpler version, and the other tags say what to add and when.
See "Reading the code" in `docs/technical.md`.

`my_app/modules/example.py`, `my_app/client.py` (the API example, with
its address, endpoint and ID rule), their tests, and the text in `docs/`
and `README.md` are placeholders. Replace them with the real project.
If your project does not call a web API, delete `client.py`,
`tests/test_client.py` and the `requests` line in `pyproject.toml`.
