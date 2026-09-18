#!/usr/bin/env bash
# Dump the household database, verify the dump, keep a rotating set, and copy
# it off the device. Run by home-backup.timer; safe to run by hand.
#
# Three things a backup usually fails at, each handled explicitly:
#   - it silently produces nothing: every dump is verified by listing it
#   - it only exists on the device that can die: rsync to OFFSITE if set
#   - nobody notices when it breaks: exit non-zero, and the failure unit
#     sends a push notification if NTFY_TOPIC is set (see SETUP.md)
set -euo pipefail

: "${HOME_DATA_DIR:?HOME_DATA_DIR is not set (source deploy/.env)}"
DIR="$HOME_DATA_DIR/backups"
DB_CONTAINER="${DB_CONTAINER:-home-deploy-db}"   # container_name in compose.override.yaml
PG_USER="${POSTGRES_USER:-home}"
PG_DB="${POSTGRES_DB:-home}"
OFFSITE="${BACKUP_OFFSITE:-}"          # e.g. lucky@laptop:backups/home  (over Tailscale)

mkdir -p "$DIR/hourly" "$DIR/daily" "$DIR/monthly"
stamp="$(date +%Y%m%d-%H%M)"
file="$DIR/hourly/home-$stamp.dump"

echo "backup: dumping $PG_DB -> $file"
docker exec "$DB_CONTAINER" pg_dump -U "$PG_USER" -Fc "$PG_DB" > "$file"

# A dump that cannot be listed is not a backup. pg_restore --list reads the
# custom-format header and table of contents, which catches a truncated or
# empty file without needing a database to restore into.
if ! docker exec -i "$DB_CONTAINER" pg_restore --list < "$file" > /dev/null; then
  echo "backup: VERIFY FAILED for $file" >&2
  rm -f "$file"
  exit 1
fi
size=$(stat -c %s "$file")
echo "backup: verified ($size bytes)"

# Promote: first dump of the day becomes the daily, first of the month the monthly.
day="$DIR/daily/home-$(date +%Y%m%d).dump"
month="$DIR/monthly/home-$(date +%Y%m).dump"
[ -e "$day" ]   || cp "$file" "$day"
[ -e "$month" ] || cp "$file" "$month"

# Retention: hourly for 2 days, daily for a month, monthly for a year.
find "$DIR/hourly"  -name '*.dump' -mtime +2   -delete
find "$DIR/daily"   -name '*.dump' -mtime +31  -delete
find "$DIR/monthly" -name '*.dump' -mtime +366 -delete

# Off the device. A copy that stays on the Pi protects against a bad
# migration, never against losing the Pi.
if [ -n "$OFFSITE" ]; then
  echo "backup: syncing to $OFFSITE"
  rsync -a --delete "$DIR/" "$OFFSITE/"
  echo "backup: offsite done"
else
  echo "backup: BACKUP_OFFSITE not set — dumps exist only on this device" >&2
fi

echo "backup: ok"
