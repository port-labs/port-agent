#!/usr/bin/env bash

set -x

mypy app tests
black app tests --check
isort --profile black --check-only app tests
flake8
