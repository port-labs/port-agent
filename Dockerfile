FROM python:3.11-alpine

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
    curl

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Ensure Poetry's bin directory is in PATH
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy pyproject.toml and poetry.lock to the container
COPY pyproject.toml poetry.lock ./

# Install Python dependencies using Poetry
RUN poetry install --no-root --no-interaction --no-ansi

# Copy the application code
COPY ./app .

# Run the application
CMD ["poetry", "run", "python3", "main.py"]
