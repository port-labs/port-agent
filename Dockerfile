FROM python:3.10-slim-buster

ENV LIBRDKAFKA_VERSION 1.9.2

WORKDIR /app

RUN apt update && \
    apt install -y wget make g++ libssl-dev autoconf automake libtool curl librdkafka-dev && \
    apt-get clean

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY ./app .

CMD [ "python3", "main.py"]
