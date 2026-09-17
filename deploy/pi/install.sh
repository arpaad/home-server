#!/usr/bin/env bash
# Install (or re-install) the systemd units. Idempotent; run after every
# `git pull` that touched deploy/pi/.
set -euo pipefail
cd "$(dirname "$0")"
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }

install -m 0644 home.service home-backup.service home-backup.timer home-backup-failed.service /etc/systemd/system/
install -m 0755 backup.sh restore.sh update.sh .
mkdir -p /etc/caddy
install -m 0644 Caddyfile /etc/caddy/Caddyfile
install -m 0644 caddy.service /etc/systemd/system/caddy.service
[ -e /etc/caddy/env ] || { install -m 0600 caddy.env.example /etc/caddy/env; echo ">> fill in /etc/caddy/env"; }

systemctl daemon-reload
systemctl enable home.service home-backup.timer caddy.service
echo "install: units enabled — start them with: sudo systemctl start home caddy home-backup.timer"
