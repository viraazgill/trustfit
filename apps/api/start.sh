#!/bin/sh
# Container entrypoint: migrate, seed an empty database (never wipes), then serve on $PORT.
set -e
python -m alembic upgrade head
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
