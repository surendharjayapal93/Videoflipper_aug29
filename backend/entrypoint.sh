#!/bin/sh
# Applies pending Alembic migrations before starting the app, so a fresh
# `docker-compose up` on an empty Postgres volume doesn't need a manual
# `alembic upgrade head` run by hand.
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"
