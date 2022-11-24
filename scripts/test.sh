#!/usr/bin/env bash

set -e
set -x

PYTHONPATH=app STREAMER_NAME=test PORT_ORG_ID=test_org pytest --cov=app --cov-report=term-missing tests "${@}"
