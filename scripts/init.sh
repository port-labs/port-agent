#!/bin/bash
# Only emptyDir mounted at /tmp/port-agent is guaranteed writable

set -e

# Ensure HOME points to writable emptyDir location
export HOME="${HOME:-/tmp/port-agent}"

# Create required directories in writable location
mkdir -p /tmp/port-agent/ca-certificates

# Sync CA certificates to writable location
source /app/scripts/sync_ca_certs.sh

exec /app/.venv/bin/python main.py
