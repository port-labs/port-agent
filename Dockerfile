ARG AWS_ACCOUNT_ID
ARG BASE_PYTHON_IMAGE=${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/echo/python:3.11

FROM ${BASE_PYTHON_IMAGE} AS base

ENV LIBRDKAFKA_VERSION=1.9.2

# Install system dependencies and libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    librdkafka-dev \
    build-essential \
    bash \
    libonig-dev \
    autoconf \
    automake \
    libtool \
    curl \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

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

ARG AWS_ACCOUNT_ID
ARG BASE_PYTHON_IMAGE=${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com/echo/python:3.11

FROM ${BASE_PYTHON_IMAGE} AS prod

ARG AGENT_USER_ID=1000

ENV LIBRDKAFKA_VERSION=1.9.2

# Create a dedicated user and group
RUN groupadd --gid ${AGENT_USER_ID} appgroup && \
    useradd --uid ${AGENT_USER_ID} --gid appgroup --shell /bin/bash --create-home agent

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    librdkafka-dev \
    libonig-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependencies from the build stage
COPY --from=base /app /app

# Copy the application code
COPY ./app/. .

# Clean up old setuptools
RUN pip uninstall -y setuptools || true

# Copy startup scripts
COPY ./scripts/sync_ca_certs.sh /app/scripts/sync_ca_certs.sh
COPY ./scripts/init.sh /app/scripts/init.sh
RUN chmod +x /app/scripts/sync_ca_certs.sh /app/scripts/init.sh

# Change ownership of /app to agent user
RUN chown -R agent:appgroup /app

# Switch to agent user
USER agent

# Run the application
CMD ["bash", "/app/scripts/init.sh"]
