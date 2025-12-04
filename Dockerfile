FROM python:3.11-alpine3.19 AS base

ENV LIBRDKAFKA_VERSION=1.9.2

# Install system dependencies and libraries
RUN apk add --no-cache \
    gcc \
    musl-dev \
    librdkafka-dev \
    build-base \
    bash \
    oniguruma-dev \
    make \
    autoconf \
    automake \
    libtool \
    curl \
    libffi-dev  # Added libffi-dev for compatibility with some packages

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.8.3 python3 -

# Ensure Poetry's bin directory is in PATH
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy pyproject.toml and poetry.lock to the container
COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true

# Install Python dependencies using Poetry
RUN poetry install --without dev --no-ansi

FROM python:3.11-alpine3.19 AS prod

ENV LIBRDKAFKA_VERSION=1.9.2

# Install only runtime dependencies
RUN apk add --no-cache \
    librdkafka-dev \
    bash \
    oniguruma-dev

WORKDIR /app

# Copy dependencies from the build stage
COPY --from=base /app /app

# Copy the application code
COPY ./app/. .

# Clean up old setuptools
RUN pip uninstall -y setuptools || true

# Run the application
CMD ["sh", "-c", "update-ca-certificates && /app/.venv/bin/python main.py"]
