#!/usr/bin/env bash

set -e
set -x

cd ./app && PYTHONPATH=./ STREAMER_NAME=test PORT_ORG_ID=test_org pytest --cov=./ --cov-report=term-missing ../tests "${@}"
