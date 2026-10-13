#!/bin/sh
# Applies pending Alembic migrations before the API starts, so a fresh
# `docker-compose up` against an empty PostgreSQL database ends up with a
# real schema instead of every request 500ing on a missing table. Runs
# every start (not just the first) - a no-op against an already-current
# database, and the only way a second/replica container also picks up a
# migration applied by another instance.
set -e

python -m alembic upgrade head

exec "$@"
