#!/bin/sh
# Bring the deployment to a usable state before serving, so a fresh container
# against an empty database needs no manual step.
#
# All three steps are safe to repeat: waiting is idempotent by nature,
# `alembic upgrade head` is a no-op once migrated, and seeding inserts only
# what is missing. That matters because this runs on every container start,
# not just the first.
set -eu

# The database is waited for here, not left to compose's depends_on: older
# podman skips the service_healthy condition without complaint, and after a
# power cut the two containers race regardless of what compose intended.
echo "entrypoint: waiting for the database"
python - <<'PY'
import sys
import time

import psycopg

from app.core.config import get_settings

url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://", 1)
deadline = time.monotonic() + 120
while True:
    try:
        psycopg.connect(url, connect_timeout=3).close()
        break
    except psycopg.OperationalError as exc:
        if time.monotonic() > deadline:
            print(f"entrypoint: database not reachable after 120s: {exc}", file=sys.stderr)
            sys.exit(1)
        time.sleep(1)
PY

echo "entrypoint: migrating to head"
alembic upgrade head

echo "entrypoint: seeding household members"
python -m app.db.seed

echo "entrypoint: starting $*"
exec "$@"
