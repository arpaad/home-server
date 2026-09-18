#!/usr/bin/env bash
# Update the Pi to the latest published image: pull, then restart the stack.
# The API container migrates and seeds on start, so this is the whole upgrade.
set -euo pipefail
cd /opt/home-server
git pull --ff-only
docker compose -f deploy/compose.deploy.yaml -f deploy/pi/compose.override.yaml pull
systemctl restart home
sleep 5
curl -fsS http://127.0.0.1:8080/health && echo && echo "update: ok"
