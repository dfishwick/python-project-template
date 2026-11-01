# Installation

This page explains how to set the project up and start it. The
[user guide](user-guide.md) explains how to use it once it is running.

## Requirements

- Git
- Conda (for example Miniconda)

Conda provides Python 3.12. Every other package is installed with pip and
pinned to an exact version in `pyproject.toml`.

## Steps

1. Download the code:

    ```
    git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
    cd YOUR_REPO
    ```

2. Create the environment from `environment.yml`:

    ```
    conda env create -f environment.yml
    ```

3. Activate it:

    ```
    conda activate my-app
    ```

4. Install the app and its packages:

    ```
    python -m pip install -e .
    ```

5. Start the app:

    ```
    flask --app my_app.main:create_app run
    ```

6. Open `http://127.0.0.1:5000/` in a browser.

To run the app in a container instead, see [Docker](docker.md).
