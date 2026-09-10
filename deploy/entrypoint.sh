#!/bin/sh
# Bring the schema up to date before serving, so a fresh container against an
# empty database ends up fully migrated with no manual step.
set -eu

echo "entrypoint: migrating to head"
alembic upgrade head

echo "entrypoint: starting $*"
exec "$@"
