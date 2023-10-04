FROM python:3.10-slim-buster
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

ENV LIBRDKAFKA_VERSION 1.9.2
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"
WORKDIR /app

RUN apt update && apt install -y wget make g++ libssl-dev curl
RUN wget https://github.com/edenhill/librdkafka/archive/v${LIBRDKAFKA_VERSION}.tar.gz &&  \
    tar xvzf v${LIBRDKAFKA_VERSION}.tar.gz &&  \
    (cd librdkafka-${LIBRDKAFKA_VERSION}/ && ./configure && make && make install && ldconfig)

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry config virtualenvs.in-project true

COPY ./pyproject.toml ./poetry.lock ./
RUN poetry install --no-root --without test,lint

COPY ./app .

CMD ["poetry", "run", "python", "main.py"]

