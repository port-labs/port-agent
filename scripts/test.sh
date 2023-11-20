#!/usr/bin/env bash

set -e
set -x

cd ./app && PYTHONPATH=./ STREAMER_NAME=test PORT_ORG_ID=test_org PORT_CLIENT_ID=test PORT_CLIENT_SECRET=test pytest --cov=./ --cov-report=term-missing ../tests "${@}"
