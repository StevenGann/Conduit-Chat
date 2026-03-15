#!/bin/sh
set -e
mkdir -p /app/data
chown conduit:conduit /app/data 2>/dev/null || true
exec runuser -u conduit -- "$@"
