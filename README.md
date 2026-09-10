# H.O.M.E. — Household Operations, Management & Essentials

A household management system for one family. FastAPI and PostgreSQL on the
backend, a React progressive web app on the front, running on a Raspberry Pi
in the house.

> **This release has no authentication.** Members are identified so that
> purchases can be attributed, not authenticated. It is intended to be
> reachable from the household network only. **Do not expose it to the
> internet or port-forward it** until the authentication change lands.

## What it does today

One shared shopping list. Every item is written once and carries the stores
it may be bought at, so standing in Lidl shows exactly what to put in the
basket — including items tied to no store at all. Checking something off
removes it everywhere, which is the point: the per-store lists it replaces
caused the same item to be bought twice.

Items can also carry a date they become worth buying, so "it's on sale next
week" stops being something anyone has to remember.

Planned modules — recipes, tasks, calendar, finance — are not built. The data
model is shaped so they can attach later without a migration that loses
history.

## Layout

```
backend/     FastAPI application, tests, migrations   (Python 3.14, uv)
frontend/    React + TypeScript PWA                   (Vite, npm)
deploy/      Container image and compose definitions
openspec/    Specifications and changes
Makefile     Every routine action, for both halves
```

`openspec/` is where the specifications live. A capability's spec and the
change that implements it are versioned beside the code, so a change and its
justification are reviewed together.

## Getting started

You need [mise](https://mise.jdx.dev/) (or node 24 and uv yourself) and
Podman with a compose provider.

```bash
mise install                     # node + uv, pinned in mise.toml
make install-dev-dependencies    # backend deps + pre-commit hooks
make client-install              # client deps

make db-reset                    # Postgres from nothing: migrate + seed
make up                          # the whole stack on http://127.0.0.1:8080
```

`make up` builds an image that serves the API *and* the built client on one
port. For working on the client, run the two separately:

```bash
make db-up && make run           # API on :8080
make client-dev                  # client on :5173, proxying /api
```

Set the household's members before first use — the seed defaults to
`Árpád` and `Partner`:

```bash
export HOME_HOUSEHOLD_MEMBERS='["Árpád","<the other name>"]'
```

## Database and migrations

The schema comes from Alembic revisions, never from `create_all`. Importing
the application creates no tables: the schema a container starts against is
always the one a migration produced.

| Command                    | What it does                                     |
| -------------------------- | ------------------------------------------------ |
| `make db-up`               | Start Postgres; create the test database if missing |
| `make db-down`             | Stop Postgres, keeping its data                  |
| `make migrate`             | Apply every migration up to head                 |
| `make migration m="…"`     | Autogenerate a revision from the ORM models      |
| `make seed`                | Insert the configured household members          |
| `make db-reset`            | Drop the volume and rebuild from nothing         |

After changing an ORM model, run `make migration m="what changed"`, read the
generated file, and commit it. Autogenerate is a starting point, not an
oracle.

The API container migrates and seeds on start, both idempotent, so a fresh
deployment needs no manual step.

## Checks

```bash
make lint-all       # ruff, pyright, oxlint, tsc — both halves
make test           # backend tests (needs the database)
make coverage       # the same, with a coverage report
make e2e            # Playwright, against a real backend
make security-audit # dependency audit
```

Backend tests run against **real PostgreSQL**, not SQLite, and build their
schema by running the migrations — so every test run exercises the migration
path too. The store-and-availability filter is expressed in SQL, and testing
it against a different engine would test something other than what ships.

## Deployment

CI publishes a multi-architecture image to GHCR on every tag. The target
machine pulls it; it never builds.

```bash
cp deploy/.env.example deploy/.env    # set HOME_BIND_ADDRESS and a password
make deploy-pull
make deploy-up
```

`deploy/compose.deploy.yaml` runs the published image with Postgres beside
it, on a named volume, with restart policies on both. Postgres is not
published on the host at all. The published API port defaults to loopback;
set `HOME_BIND_ADDRESS` to the machine's LAN address — and to nothing else,
because there is no login.

Updating is deliberate (`make deploy-pull`), so a machine coming back from a
power cut returns to the version it was running rather than whatever is
newest.

### Not yet done

Running this on the Pi still needs: the data volume placed on external
storage rather than the SD card, systemd units so the stack starts at boot,
and scheduled off-device backups with a rehearsed restore. Those are tasks
8.3–8.9 of the `add-shopping-list` change. **Do not let the household depend
on this service before the backup and restore work is finished.**

## Tools

| Tool                | Purpose                                             |
| ------------------- | --------------------------------------------------- |
| **mise**            | Pins node and uv for this repository                |
| **uv**              | Python dependencies, locked in `backend/uv.lock`    |
| **Ruff**            | Linting and formatting, with a strict rule set      |
| **Pyright**         | Static type checking, strict mode                   |
| **Alembic**         | Database migrations                                 |
| **Vite / oxlint**   | Client build and linting                            |
| **Playwright**      | End-to-end tests in a real browser                  |
| **pre-commit**      | Formats and lints before a commit lands             |
| **Podman**          | Containers, locally and on the Pi                   |
| **GitHub Actions**  | Checks on every branch; multi-arch publish on tags  |
