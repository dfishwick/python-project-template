# Dockerfile: the recipe for the image the app runs in. An image is a
# packaged copy of the app plus everything it needs, so it behaves the same
# on your laptop, on GitHub's servers and on a lab machine.
#
# WHAT TO BUILD FIRST (importance ranking)
# 1. [CORE] FROM, COPY, RUN pip install, CMD. Four instructions are a
#    working image.
# 2. [SECONDARY] WORKDIR, EXPOSE: tidier and self-documenting.
# 3. [SAFETY] Never copy credentials into the image. Anything inside it can
#    be read by anyone who gets the image. See .dockerignore.
#
# [CORE] FROM picks the starting image. Pinning the exact Python version
# (not just "3.12") means a rebuild next year gives the same Python.
# "slim" is a smaller image without extras this app does not need.
# Pinned base image: same Python as environment.yml
FROM python:3.12.14-slim

# [SECONDARY] WORKDIR sets the folder inside the image where later
# instructions run, and creates it if needed.
# All later instructions run from /app inside the image
WORKDIR /app

# [CORE] COPY <from> <to>: first "." is your project folder, second "." is
# the current folder inside the image (/app). .dockerignore lists files to
# leave out.
# Copy the build context (minus .dockerignore entries)
COPY . .

# [CORE] RUN executes a command while the image is BUILT. `--no-cache-dir`
# stops pip keeping download files, so the image is smaller. `-e .` installs
# this project itself from pyproject.toml, with its pinned dependencies.
# Install the app and its pinned dependencies from pyproject.toml
RUN pip install --no-cache-dir -e .

# [SECONDARY] EXPOSE is documentation only: it does not open the port. The
# port is opened by `docker run -p 8000:8000`.
# Document the port the app listens on
EXPOSE 8000

# [CORE] CMD is the command run when a container STARTS (RUN is when the
# image is built). `--app my_app.main:create_app` tells Flask to call the
# factory function in my_app/main.py. `--host=0.0.0.0` listens on every
# network address; the default (127.0.0.1) would be unreachable from outside
# the container.
# Start Flask, listening on all interfaces so the host can reach it
CMD ["flask", "--app", "my_app.main:create_app", "run", "--host=0.0.0.0", "--port=8000"]
