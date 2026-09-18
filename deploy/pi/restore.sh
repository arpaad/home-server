#!/usr/bin/env bash
# Restore a dump into the running database. Rehearse this BEFORE the
# household depends on the service — an untested backup is a hope.
#
#   sudo ./restore.sh /mnt/home-data/backups/daily/home-20260917.dump
#
# --clean --if-exists drops and recreates every object first, so the result
# is the dump, not the dump merged into whatever was there.
set -euo pipefail

dump="${1:?usage: restore.sh <file.dump>}"
DB_CONTAINER="${DB_CONTAINER:-home-deploy-db}"
PG_USER="${POSTGRES_USER:-home}"
PG_DB="${POSTGRES_DB:-home}"

echo "restore: listing $dump"
docker exec -i "$DB_CONTAINER" pg_restore --list < "$dump" | tail -3
read -r -p "Restore this into '$PG_DB', REPLACING its contents? [type yes] " answer
[ "$answer" = "yes" ] || { echo "aborted"; exit 1; }

docker exec -i "$DB_CONTAINER" pg_restore -U "$PG_USER" -d "$PG_DB" --clean --if-exists --no-owner < "$dump"
echo "restore: done — items now: $(docker exec "$DB_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -tAc 'select count(*) from shopping_items')"
