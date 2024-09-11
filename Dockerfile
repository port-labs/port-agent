FROM python:3.11-alpine

ENV LIBRDKAFKA_VERSION 1.9.2

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
    libtool

WORKDIR /app

# Upgrade pip to the latest version
RUN pip install --upgrade pip

# Copy and install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY ./app .

# Run the application
CMD [ "python3", "main.py" ]
