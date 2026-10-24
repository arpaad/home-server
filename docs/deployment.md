# How H.O.M.E. runs on the Pi

The Pi does not hold a checkout of this repository. It runs the image CI
publishes (`ghcr.io/arpaad/home-server:latest`) with a handful of
hand-written files, all reproduced below. This page is the source of truth
for what those files contain, so they can be read and edited from here
without logging in to compare.

Secrets are shown as `<…>`. The real values exist only on the Pi.

Recorded 2026-10-24, from the running machine.

## The machine

- Raspberry Pi, arm64, Ubuntu, a single 32 GB SD card, no external disk.
- Podman from apt, and `podman-compose` installed with pipx into
  `/usr/local/bin`. That path matters because systemd units call it by
  absolute path.
- Reached by SSH from the home network only. It has no remote access, and the
  app has none either: away from home the phones use the PWA offline and
  synchronise when they are back on the home Wi-Fi.

## What is where

| Path                                 | What                                              |
| ------------------------------------ | ------------------------------------------------- |
| `/opt/home/compose.yaml`             | The stack: Postgres and the API                   |
| `/opt/home/.env`                     | `POSTGRES_PASSWORD`, mode 600                     |
| `/var/lib/home/postgres/`            | The database's files (bind mount)                 |
| `/var/lib/home/backups/`             | Dumps taken by `make update` / `make backup`      |
| `/etc/systemd/system/home.service`   | Starts the stack at boot                          |
| `~lucky/Makefile`                    | Day-to-day operations: update, backup, logs       |
| `/usr/local/bin/caddy`               | Caddy, built with the DuckDNS module              |
| `/etc/caddy/Caddyfile`               | HTTPS in front of the API                         |
| `/etc/caddy/env`                     | `HOME_DOMAIN`, `DUCKDNS_TOKEN`, mode 600          |
| `/etc/systemd/system/caddy.service`  | Runs Caddy as the `caddy` system user             |

## Operations

All of these run from the home directory, as root:

```bash
sudo make update    # dump the database, pull :latest, recreate, wait for /health
sudo make backup    # dump the database only
sudo make version   # which image version is running
sudo make status    # podman ps -a
sudo make logs      # follow the API's log
```

`update` takes a dump first because the new container migrates on start,
and a migration cannot be undone. If the pull fails, `down` never runs and
the old version stays up.

To start, stop or restart the whole stack:

```bash
sudo systemctl restart home
sudo systemctl restart caddy
journalctl -u caddy -f
```

### Restore

This has **not** been tried yet. Stop the API so nothing writes during the
restore, restore the dump over the existing database, and start the stack
again:

```bash
sudo podman stop home-deploy-api
sudo podman exec -i home-deploy-db \
  pg_restore -U home -d home --clean --if-exists \
  < /var/lib/home/backups/home-YYYY-MM-DD-HHMM.dump
sudo systemctl restart home
```

## The files

### `/opt/home/compose.yaml`

```yaml
name: home-deploy

services:
  db:
    image: docker.io/library/postgres:18-alpine
    container_name: home-deploy-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: home
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: home
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - /var/lib/home/postgres:/var/lib/postgresql/data

  api:
    image: ghcr.io/arpaad/home-server:latest
    container_name: home-deploy-api
    restart: unless-stopped
    depends_on: [db]
    environment:
      HOME_ENVIRONMENT: production
      HOME_DATABASE_URL: postgresql+psycopg://home:${POSTGRES_PASSWORD}@db:5432/home
      HOME_HOUSEHOLD_TIMEZONE: Europe/Budapest
      HOME_HOUSEHOLD_MEMBERS: '["<member 1>","<member 2>"]'
    ports:
      - "8080:8080"
```

Why it looks like this:

- **`PGDATA` is set explicitly.** The postgres 18 image keeps its data under
  `/var/lib/postgresql/18/docker` by default, and that path is *not* inside
  the bind mount. Without the `PGDATA` line, the database would live in an
  anonymous volume and could be replaced by an empty one whenever
  `make update` recreates the container. Do not remove it. The image still
  declares `/var/lib/postgresql` as a volume, so every recreate leaves an
  empty anonymous volume behind. They are harmless, and
  `sudo podman volume prune` clears them.
- **`depends_on` has no health condition.** The image's entrypoint waits
  up to two minutes for the database itself (see `deploy/entrypoint.sh`),
  because podman-compose does not reliably honour `service_healthy`.
- **Fixed container names**, because the Makefile refers to them.
- **`ports: "8080:8080"`** publishes on every interface. That makes the API
  reachable over plain HTTP from the LAN, bypassing Caddy. Caddy connects to
  `127.0.0.1:8080`, so `"127.0.0.1:8080:8080"` would be enough and would leave
  HTTPS as the only way in.
- The API migrates and seeds on every start, and both are idempotent. The
  household members are set from `HOME_HOUSEHOLD_MEMBERS`.

### `/opt/home/.env`

```
POSTGRES_PASSWORD=<openssl rand -hex 24>
```

### `/etc/systemd/system/home.service`

```ini
[Unit]
Description=H.O.M.E.
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/home
ExecStart=/usr/local/bin/podman-compose up -d
ExecStop=/usr/local/bin/podman-compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

`restart: unless-stopped` only restarts containers while podman is already
running. After a reboot, this unit is what brings them back.

### `~lucky/Makefile`

Recipes are indented with real tabs.

```make
# H.O.M.E. a Pi-n. Mindig sudo-val: sudo make update
SHELL = /bin/bash
COMPOSE = cd /opt/home && podman-compose
IMAGE = ghcr.io/arpaad/home-server:latest
BACKUPS = /var/lib/home/backups

.PHONY: update backup version status logs

# Előbb mentés (a migráció nem vonható vissza), aztán pull. Ha a pull elhasal,
# a régi verzió fut tovább. Az új konténer indulásakor lefut a migráció.
update: backup
	$(COMPOSE) pull api
	$(COMPOSE) down
	$(COMPOSE) up -d
	@for i in $$(seq 60); do curl -fsS http://127.0.0.1:8080/health && echo && exit 0; sleep 2; done; echo "!! 2 perc után sem válaszol: sudo make logs"; exit 1
	@$(MAKE) --no-print-directory version
	podman image prune -f

backup:
	mkdir -p $(BACKUPS)
	podman exec home-deploy-db pg_dump -U home -Fc home > $(BACKUPS)/home-$$(date +%F-%H%M).dump
	@ls -lh $(BACKUPS) | tail -3

version:
	@echo "fut: $$(podman image inspect $(IMAGE) --format '{{index .Labels "org.opencontainers.image.version"}}')"

status:
	podman ps -a

logs:
	podman logs --tail 100 -f home-deploy-api
```

### `/etc/caddy/Caddyfile`

```
{$HOME_DOMAIN} {
    tls {
        dns duckdns {$DUCKDNS_TOKEN}
    }
    encode gzip
    reverse_proxy 127.0.0.1:8080
}
```

HTTPS is required even with no remote access: the PWA only installs, and its
service worker (the offline mode) only runs, in a secure context, and a LAN
IP is not one. Caddy gets a real Let's Encrypt certificate by proving
control of the DuckDNS name through DNS. Nothing has to be reachable from the
internet, and it renews itself.

### `/etc/caddy/env`

```
HOME_DOMAIN=<name>.duckdns.org
DUCKDNS_TOKEN=<token>
```

### `/etc/systemd/system/caddy.service`

```ini
[Unit]
Description=Caddy (HTTPS for H.O.M.E.)
After=network-online.target
Wants=network-online.target

[Service]
User=caddy
Group=caddy
EnvironmentFile=/etc/caddy/env
ExecStart=/usr/local/bin/caddy run --environ --config /etc/caddy/Caddyfile
ExecReload=/usr/local/bin/caddy reload --config /etc/caddy/Caddyfile --force
TimeoutStopSec=5s
LimitNOFILE=1048576
PrivateTmp=true
ProtectSystem=full
AmbientCapabilities=CAP_NET_BIND_SERVICE
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

The binary comes from Caddy's download service with the DuckDNS module
compiled in. Stock Caddy cannot solve the DNS challenge:

```bash
sudo curl -fsSL -o /usr/local/bin/caddy \
  'https://caddyserver.com/api/download?os=linux&arch=arm64&p=github.com/caddy-dns/duckdns'
sudo chmod +x /usr/local/bin/caddy
sudo useradd --system --home /var/lib/caddy --create-home \
  --shell /usr/sbin/nologin caddy
```

## Known gaps

The design (`openspec/changes/add-shopping-list/design.md`, durability
section) asks for more than this. What is missing:

- **The database is on the SD card.** The design puts it on external storage,
  because SD cards corrupt under power loss.
- **Backups happen only on `make update` / `make backup`.** No timer takes
  them, nothing checks them, and they stay on the Pi. That protects against a
  bad migration, but not against losing the card or the Pi.
- **The restore has never been run.**
- **Rebooting has not been verified** to bring the list back with no manual
  step.
