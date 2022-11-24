#!/bin/sh -e
set -x

autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place app tests --exclude=__init__.py
black app tests
isort --profile black app tests
