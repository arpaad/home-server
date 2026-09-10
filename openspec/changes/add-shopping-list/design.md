## Context

See `proposal.md` — Why, for the motivation. This section covers only the state of the target repository that shapes the approach.

This change targets the repository it lives in: H.O.M.E., a FastAPI backend whose README already declares Shopping, Recipes, Tasks, Calendar and Finance as intended modules. What exists today:

- A clean intended layering — `app/modules/<module>/{domain, dto, repository, service, api}` with a `Protocol`-typed repository — but the shopping module **does not follow it**: `service/shopping_list_service.py` is empty and the routes call the repository directly.
- `ShoppingListItem` with name, quantity and unit only. An ORM `list_id` column that nothing reads, and a `ShoppingListORM` table with no domain or service behind it.
- `app/db/session.py` defaults to SQLite and calls `init_tables()` at **import time**, so importing the module creates schema as a side effect. No migration tooling.
- `app/core/config.py` is empty; configuration is read ad hoc from `os.getenv`.
- The repository is a single root-level Python project: `app/`, `tests/`, `pyproject.toml`, `Makefile` and `Dockerfile` all sit at the top level. There is no compose file, and the Makefile has no database targets at all — `start-container` runs one lone container with no database behind it.
- Strict tooling already in place: ruff with a wide rule set (including `DTZ`, which forbids naive datetimes, and `TRY`, `S`, `DOC`), pyright, pytest with coverage, pre-commit, GitHub Actions, Dockerfile.
- Effectively no test coverage of behaviour: `tests/test_main.py` only.

Deployment constraints: a Raspberry Pi running Podman, two users, exposed on the household LAN only. Frontend does not exist yet in this repository.

The user's decision on stack was explicit: the household project stays Python precisely because their professional work is moving to Go, so this repository is the Python reference. That settles the language question on grounds that no benchmark can override.

## Goals / Non-Goals

**Goals:**

- Make the store-and-availability filter a property of the data model and the query, not of client-side filtering, so the rule holds for every client.
- Make it impossible to reference a store that does not exist, at the database level rather than by convention.
- Establish one seam for "who is acting" so the deferred authentication change replaces one function rather than every endpoint.
- Record a purchase as an event that a later purchase log, price history and finance module can extend without a data migration.
- Bring the shopping module in line with the layering the repository already claims to use.

**Non-Goals:**

- Real-time push between the two clients. Refetching on focus is sufficient at this scale.
- Any abstraction over the database engine beyond what SQLAlchemy already gives.
- Generalised tagging. Each new facet gets its own typed field, by explicit decision (see Decisions).

## Decisions

### Python 3.13 + FastAPI, continuing the H.O.M.E. repository

**Chosen because** the repository already has the architecture, tooling, CI and container setup this change needs, and because the user wants a Python reference project alongside Go professional work.

**Alternatives considered.** *Go + Gin*: genuinely lower memory on a Pi (roughly 20 MB versus 100+ MB) and a single static binary, but at two users and a few dozen requests a day the performance argument is irrelevant, and it would discard the existing investment. *A fresh Python repository*: rejected — the existing layering is sound; what is wrong is that the shopping module does not follow it, which this change fixes anyway.

### PostgreSQL, not MariaDB, SQLite or a graph database

**Chosen because** the modules this list must eventually feed decide it. Finance needs exact `NUMERIC` money (never floating point) and window functions for balance and interest history; `JSONB` gives per-module extension without schema churn; partial and expression indexes support the "outstanding items only" queries this capability runs constantly.

**Alternatives considered.** *SQLite*: at two users with WAL enabled it would genuinely suffice and needs no operational work — it is a defensible choice, rejected only for the future modules' numeric and analytic needs. *MariaDB*: workable but weaker on every point above. *A graph database*: rejected outright. The data is relational; the "recipe → ingredient → purchase" traversal the user imagined is a two- or three-table join, not a graph problem, and running one on a Pi costs memory and operational burden for no benefit.

### Named, typed facets instead of a generic label bag

An item carries a `stores` relation and an `available_from` date as distinct, named fields. Future facets (urgency, category) will each get their own field.

**Chosen because** a shared label bag forces the filter to encode which label means what, as undocumented knowledge in code. With named fields, "no store means every store" is a stated domain rule rather than an implicit convention, and each facet gets validation appropriate to its own type — a date is a date, not a string called `"next-week"`.

**Alternatives considered.** *A generic `labels` array*: fewer tables and trivially extensible, rejected for the reasons above. The user independently proposed the named-field approach.

### Stores as a table with a foreign key, not a string array

`shopping_item_stores` is a join table with foreign keys to `stores`.

**Chosen because** referential integrity is the point, not tidiness. A free-text store name lets a typo (`"lidll"`) silently remove an item from its store's view, with no error — reproducing exactly the failure this capability exists to eliminate. A foreign key makes that unrepresentable, and it is what lets the system refuse to delete a store that items still reference.

**Alternatives considered.** *A Postgres `uuid[]` column with a GIN index*: fewer joins and fast, but no referential integrity, which is the requirement. *Free-text names with normalisation on write*: still allows a normalised typo to become a new store.

### Purchase as a separate event row, not nullable columns on the item

A purchase is a row in `shopping_item_purchases` referencing the item, the member and the time. An item is outstanding when it has no purchase row; undo deletes the row.

**Chosen because** price, receipt and finance links attach to the *purchase*, not to the item, and a staple bought repeatedly has a history of purchases. Modelling it now costs one table; modelling it later costs a migration and the history already lost.

**Alternatives considered.** *`bought_at` / `bought_by` nullable columns on the item*: simpler today, but conflates "what we want" with "what we bought" and forces the item table to grow every commercial attribute later.

### The filter is evaluated in SQL

The store-and-availability predicate is expressed as a single query:

```
outstanding      : NOT EXISTS (purchase for this item)
available now    : available_from IS NULL OR available_from <= <household today>
store matches    : NOT EXISTS (any store link)            -- "anywhere"
                   OR EXISTS (store link = selected store)
```

**Chosen because** the "no store links means every store" rule is the correctness core of this change. Expressing it once in the repository layer keeps it identical for every caller and every future client, and keeps it correct under paging. Filtering in Python after fetching everything would work at this data size but puts the critical rule in the layer most likely to be duplicated.

### Availability compared against a configured household date

`available_from` is a `DATE`. "Today" is computed at query time in a configured household timezone (`Europe/Budapest`), never from a naive local clock — the repository's ruff `DTZ` rules already forbid the naive form.

**Chosen because** a date boundary evaluated in UTC surfaces an item at 01:00 or 02:00 local, which is visible and wrong. **Trade-off:** a member shopping abroad sees household-local behaviour; accepted as correct for a household list.

### One actor seam, ready for the deferred auth change

The client stores the chosen member locally and sends it on each request; the server resolves it in a single FastAPI dependency (`get_current_member`). Every endpoint depends on that, never on the raw header.

**Chosen because** authentication is deferred, not abandoned. When that change lands, the dependency's body is replaced with session or token validation and no endpoint changes. This is also the honest place to document that the current implementation trusts its caller absolutely, so review cannot miss it.

### REST endpoints under `/api/shopping`

```
GET    /api/shopping/items?store_id=&include_upcoming=
POST   /api/shopping/items
PATCH  /api/shopping/items/{id}
DELETE /api/shopping/items/{id}                 -- no longer wanted, not a purchase
POST   /api/shopping/items/{id}/purchase        -- mark bought, idempotent
DELETE /api/shopping/items/{id}/purchase        -- undo
GET    /api/shopping/stores
POST   /api/shopping/stores
DELETE /api/shopping/stores/{id}                -- 409 with referencing items when in use
GET    /api/household/members
```

Purchase and its undo are separate sub-resources rather than a `PATCH` of a `bought` flag, because they create and remove an event, and because it makes "buying an already-bought item" naturally idempotent — which matters when both members act at once in a shop.

Two defects in the prototype API are corrected: it returned `304 Not Modified` as an error when an update was a no-op (304 is a cache response and must carry no body), and `POST` returned no representation of the created item.

### Alembic for migrations; no schema creation on import

`init_tables()` at import time is removed. Schema comes from Alembic revisions, run as a deliberate step at deploy.

**Chosen because** `create_all` cannot alter existing tables, so the first column change in the finance or recipe module would require manual SQL against live household data.

### React + TypeScript PWA, built with Vite

Installable via a web app manifest and a service worker. The service worker precaches the application shell only; data requests always go to the network.

**Chosen because** the use case — a phone, in a shop, installed on the home screen — is exactly what a PWA covers, with one codebase and no app store. React Native remains available later if native capabilities are needed; nothing here forecloses it.

**Alternatives considered.** *Flutter*: capable, but its web story is weaker and it means a second ecosystem for a two-user app. *React Native now*: adds build and distribution overhead before there is any need for native APIs.

Data access uses a query cache with explicit loading and error states, because the "connectivity is required" requirement is precisely a requirement about how failures are shown. **The service worker must not serve cached data as if it were current**, or it would violate that requirement while appearing to satisfy it.

### The repository becomes a monorepo with `backend/` and `frontend/`

The Python project moves from the repository root into `backend/`, the client lives in `frontend/`, container and compose definitions live in `deploy/`, and the Makefile stays at the root driving both sides. `openspec/` also stays at the root: the specifications describe the whole product, not one half of it, and keeping them beside the code means a change and the code implementing it are reviewed in the same commit.

**Chosen because** a change to the API contract touches the endpoint and its caller together, and in one repository that is one commit, one review and one tag. Separate repositories buy independent release cycles, which is worth having when separate teams ship on separate schedules; here it would only mean coordinating versions for a three-minute change.

**Alternatives considered.** *A separate frontend repository*: rejected for the reason above. *Leaving Python at the root and adding `frontend/` beside `app/`*: cheaper, since nothing moves, but it leaves Python project files and a frontend directory mixed at the top level, and that asymmetry never gets fixed afterwards.

**Cost, stated plainly.** The move is not free. `pyproject.toml` package discovery, `pyrightconfig.json`, every Makefile target, the Dockerfile's `COPY app ./app`, the pre-commit hook that filters on `app/`, and both GitHub Actions workflows all reference root-relative paths. Doing it now is cheap only because the repository is nearly empty; the same move in six months would not be.

### Two containers: the API serves the built client, alongside Postgres

`home-api` and `home-db`. A multi-stage image builds the client with Node and copies the built assets into the Python runtime image, which serves them next to the API.

**Chosen because** the client is static files once built — there is no runtime process to containerise. Serving it from the same origin as the API also removes CORS from the picture entirely, rather than configuring it.

**Alternatives considered.** *A third container serving the client (nginx or Caddy)*: earns its place once there is TLS to terminate or several services to route between — and at that point it belongs in front of everything on the Pi as a host-level concern, not inside this application's compose file. This application stays two containers either way. *A separate client container without a proxy*: requires CORS configuration for no gain.

Because the API serves the client, requests to non-API paths must return the client's entry document, or reloading the page on a client-side route returns 404.

### Migrations run at container start

The API container's entrypoint runs the migrations to head before starting the server.

**Chosen because** the deployment runs exactly one replica, so two processes cannot migrate concurrently — which is the usual reason to keep migrations out of startup. In exchange, deploying is a single command instead of an ordered two-step.

**Alternatives considered.** *A separate one-shot migration container*: correct at any scale, but it adds a compose service and an ordering constraint to solve a problem a single replica does not have.

### The Makefile owns the database lifecycle

Targets cover the database from nothing: `db-up` and `db-down` for Postgres alone during local development, `db-reset` to drop the volume and rebuild from migrations and seed, `migrate` and `migration`, `seed`, and `up`, `down` and `logs` for the full stack.

**Chosen because** the repository already centralises every routine action in the Makefile, and "rebuild the database from zero" is the operation most often needed and least often remembered correctly. The compose definition needs a health check on the database with the API depending on it, since an API that starts before Postgres accepts connections is the most common startup failure.

### Durability and recovery are three separate problems

They are treated separately, because any single measure would otherwise look as though it covered all three:

1. **A container stops.** The database lives in a named volume, not in the container, so a restart loses nothing. Both services carry a restart policy, and the stack is started at boot by systemd — a Pi that loses power does not otherwise bring the stack back, and that is the most likely real outage.
2. **The Pi loses power.** Postgres is crash-safe, so a committed transaction survives. The exposure is the SD card, which corrupts under write-loss and whose cheaper variants misreport flushes, undermining that very guarantee. The data volume therefore lives on external storage rather than the SD card. This prevents the failure instead of recovering from it, and matters more than any backup policy.
3. **The hardware dies or is stolen.** Only here does a backup help — and **a backup that stays on the Pi does not help at all**. On-device copies protect against a mistaken deletion or a bad migration, never against loss of the machine.

Backups are therefore compressed custom-format dumps on a host systemd timer, not cron: `journalctl` records the runs, and `Persistent=true` takes a backup that was missed while the Pi was switched off. Retention is hourly for two days, daily for a month and monthly for a year — at well under a megabyte per compressed dump, frequency costs nothing and the recovery window is worth more than the storage. Every dump is copied off the device. The timer runs on the host, so this does not reintroduce a third container.

Two failure modes are designed against explicitly, because they are the reason backups usually turn out not to exist:

- **A backup that fails silently.** Each dump is verified by listing its contents, and the job fails loudly to a notification. A job that has written an empty file for six months is worse than no backup at all, because it is trusted.
- **A restore that has never been run.** An untested backup is a hope, not a backup. Restoring into an empty database is a task in this change, not a documented intention.

**Rejected:** WAL archiving and point-in-time recovery. It is the right answer at a scale this is not, and the operational burden would never be repaid by a household shopping list.

## Risks / Trade-offs

- **No authentication, on a network-reachable service** → Bind the service to the LAN interface, document that it must not be port-forwarded, and treat the authentication change as a hard prerequisite for any external exposure. This is the single largest known gap and it is a deliberate scope decision, not an oversight.
- **The app is unusable in a shop with poor signal, which is exactly when it is needed** → The shell is precached so the app opens and states clearly that it cannot reach the server; it never silently accepts an edit. Full offline support is a planned follow-up change, and this release's value depends on adequate connectivity in the shops used.
- **Both members act on the same item simultaneously** → Purchase is idempotent, so the second mark succeeds without duplicating. For field edits, last write wins; at two users this is acceptable and detecting it would cost more than it saves.
- **Postgres on a Raspberry Pi: memory pressure and SD card wear** → Modest `shared_buffers`, and the data volume on external storage rather than the SD card. Restarts, power loss and hardware failure are handled separately; see the durability decision above.
- **The stack does not come back after a power cut** → Restart policies plus systemd units enabled at boot, verified by actually power-cycling the Pi once rather than assuming. This is the most probable outage in a household and the one that is noticed immediately.
- **A backup job that silently produces nothing** → Every dump is verified and every failure is notified. Unmonitored backups failing unnoticed is the normal case, not the exception.
- **Backups kept only on the Pi** → Each dump is copied off the device. An on-device copy protects against mistakes, never against losing the machine.
- **Deleting a store is refused rather than cascading** → Deliberate: silently unassigning would turn a restricted item into one visible in every store, the exact bug being fixed. The cost is that a member must first edit the items, and the error must name them, or the refusal is merely annoying.
- **Replacing the prototype invalidates its tests and any local SQLite data** → Nothing depends on it and no real data exists; `test.db` is discarded.
- **Scope grew beyond "just the list"** — Postgres, migrations, a frontend and a deployment all arrive in this change → Justified because a backend without a client does not solve the problem, and because migrations retrofitted after real data exists are painful. The task breakdown sequences these so the backend is verifiable before the client is built.

## Migration Plan

1. Restructure the repository into `backend/`, `frontend/` and `deploy/`, repointing every configuration file and workflow that references root-relative paths. Verify the existing suite still runs before anything else changes.
2. Introduce configuration and Alembic against a Postgres container, with the prototype's routes still present but unregistered.
3. Create the new schema in one initial revision; there is no data to migrate.
4. Build the new shopping module behind `/api/shopping`, then delete the prototype module and its `/shopping-items` routes in the same change.
5. Add the client workspace and extend the image to build it and serve it from the API.
6. Deploy with Podman: the API and Postgres containers plus a named volume on external storage, bound to the LAN interface and started at boot by systemd.
7. Enable the backup timer and perform one restore into an empty database before the household starts relying on the service.

**Rollback:** the previous container image plus a dump taken before deploy. Because this is the first real release, rollback means reverting to a service nobody depends on yet.

## Open Questions

These can be answered later without changing the specs, the approach or the task breakdown:

- Whether units should become a lookup table with conversions. The recipe module will force this question; the current fixed unit set is sufficient until then.
- Whether stores later carry address, opening hours or geolocation, which would enable "you are near Lidl" reminders.
- Whether both household phones are Android or one is iOS. iOS PWA installation works but has weaker storage guarantees; this affects polish, not architecture.
