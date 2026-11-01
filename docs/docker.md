# Docker

The `Dockerfile` builds an image with Python, the app and its pinned
packages, and starts Flask on port 8000.

## Build

```
docker build -t my-app .
```

## Run

```
docker run --rm -p 8000:8000 my-app
```

Open `http://localhost:8000/` in a browser. Press `Ctrl+C` to stop it.

## Settings

Pass a setting with `-e`, for example to show debug messages in the
terminal:

```
docker run --rm -p 8000:8000 -e MY_APP_STREAM_LOG_LEVEL=DEBUG my-app
```

See [Logging](logging.md) and [Credentials](credentials.md) for the
available settings. Never copy a credentials file into the image.

## Run the tests in the container

```
docker run -d --name my-app -p 8000:8000 my-app
docker exec my-app python -m pytest
docker rm -f my-app
```

The same steps run in GitHub Actions on every pull request.
