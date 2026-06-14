#!/bin/sh
set -eu

/app/.venv/bin/python -m concord.storage.db

exec /app/.venv/bin/uvicorn concord.api.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-10000}" \
  --proxy-headers
