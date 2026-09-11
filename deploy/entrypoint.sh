#!/bin/sh
# Bring the deployment to a usable state before serving, so a fresh container
# against an empty database needs no manual step.
#
# Both operations are safe to repeat: `alembic upgrade head` is a no-op once
# migrated, and seeding inserts only the members that are missing. That
# matters because this runs on every container start, not just the first.
set -eu

echo "entrypoint: migrating to head"
alembic upgrade head

echo "entrypoint: seeding household members"
python -m app.db.seed

echo "entrypoint: starting $*"
exec "$@"
