# Pinned base image: same Python as environment.yml
FROM python:3.12.14-slim

# All later instructions run from /app inside the image
WORKDIR /app

# Copy the build context (minus .dockerignore entries)
COPY . .

# Install the app and its pinned dependencies from pyproject.toml
RUN pip install --no-cache-dir -e .

# Document the port the app listens on
EXPOSE 8000

# Start Flask, listening on all interfaces so the host can reach it
CMD ["flask", "--app", "my_app.main:create_app", "run", "--host=0.0.0.0", "--port=8000"]
