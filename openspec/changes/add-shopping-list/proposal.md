## Why

The household currently keeps one shopping list per store (a workaround for "buy the ketchup at Lidl or Spar, but not at Aldi"). Because an item needed from either of two stores must be written on **both** lists, and checking it off in one store does not remove it from the other, the same item gets bought twice. The workaround that fixed one problem created a worse one.

There is also no way to record "I added this because it goes on sale next week — don't buy it yet", so the list cannot answer the only question that matters while standing in a shop: **"I am in Lidl right now, what should I put in the basket?"**

H.O.M.E. already declares Shopping as a module and has a prototype item CRUD, but it has no notion of stores, timing, or a shared household list. This change establishes the shopping list capability properly, as the first real slice of H.O.M.E.

## What Changes

- **One shared household list replaces per-store lists.** Every item is written once. Checking it off removes it everywhere, by construction.
- **Items carry zero or more stores.** An item with no store means "anywhere" and therefore appears under *every* store's filter. This is the rule that eliminates duplicate purchases.
- **Stores are a first-class entity**, not free text. A typo in a free-text store name would silently hide an item from its store filter — reproducing the exact failure this change exists to remove. Members pick from existing stores; adding a new store is a separate, deliberate action.
- **Items carry an "available from" date.** Until that date the item is hidden from the shopping view and surfaces automatically when the date arrives, with no manual upkeep.
- **A store-and-time filtered shopping view**: choose a store, get the items for that store plus the any-store items, excluding items not yet available.
- **Checking off an item is recorded as an event** (which member, when), not a boolean flag. This is deliberately more than the MVP needs: it is the seam that a later purchase log, price history, and the finance module attach to. Adding it later would mean a data migration and lost history.
- **Item origin is recorded** (added manually vs. derived from another source). Same reasoning: recipes will later push ingredients onto the list.
- A **React PWA** for the two household members, covering add / edit / filter / check off.
- **Postgres replaces the SQLite default**, with schema migrations. The Raspberry Pi runs Podman, so a real database is available; the finance module will need exact numeric types and window functions that SQLite handles poorly.
- **The repository becomes a monorepo.** The Python project moves from the repository root into `backend/`, the client lives in `frontend/`, and container and compose definitions live in `deploy/`, so a single commit can change an endpoint and its caller together.
- **BREAKING**: the existing prototype shopping API (`/shopping-items`) and its `ShoppingListItem` model are replaced. The prototype has no stores, no timing, no members, an unused `list_id`, an empty service layer, and routes that call the repository directly. Nothing depends on it yet, so it is replaced rather than migrated.

### Out of Scope

Deliberately excluded, each a candidate for its own later change:

- **Authentication.** The first release runs on the home LAN only. Members are *identified* (so check-off attribution works) but not *authenticated*. Using the list from inside a shop over mobile data requires a follow-up change — this is a known, accepted limitation of this release.
- **Offline use and sync.** No service worker write queue, no conflict resolution. The app requires connectivity.
- **Recipes, finance, calendar, tasks.** The data model must not preclude them; this change does not build them.
- **Price and purchase amounts.** The check-off event exists, but recording what an item cost is a later change.
- **Multiple households.** A single household is assumed.

## Capabilities

### New Capabilities

- `shopping-list`: A shared household shopping list whose items are scoped by store and by availability date, and whose completion is recorded as an attributed event. Covers item lifecycle, store management, the filtered shopping view, and shared-list visibility across household members.

### Modified Capabilities

None. `openspec/specs/` is currently empty; this is the first capability specified for H.O.M.E.

## Impact

**Repository**: H.O.M.E. — Household Operations, Management & Essentials. Planning artifacts live in `openspec/` at the repository root, versioned alongside the code they describe, so a spec and the change that implements it move together.

**Affected code**

- `backend/app/modules/shopping/**` — rewritten against the new model (domain, dto, repository, service, api). The existing layering is kept; the currently empty `service/` layer is populated and routes stop calling the repository directly.
- `backend/app/db/session.py` — Postgres engine, and removal of the import-time `init_tables()` side effect in favour of migrations.
- `backend/app/core/config.py` — currently empty; needs settings (database URL, environment).
- `backend/app/router.py` — route registration for the new endpoints.
- Repository layout — the Python project moves into `backend/`, which also means repointing `pyproject.toml`, `pyrightconfig.json`, the `Makefile`, the container definition, the pre-commit hooks and both GitHub Actions workflows.
- New: database migration tooling and initial migration.
- New: `frontend/` workspace for the PWA (not present in the repo today).
- New: `deploy/` with the container and compose definitions, and Makefile targets that build a database from nothing.

**Dependencies added**

- Backend: Postgres driver, Alembic.
- Frontend: React with a build toolchain and PWA manifest/service-worker support for installability (offline behaviour itself is out of scope).

**Deployment**

- Podman on the Raspberry Pi: two containers — an API container that also serves the built client, and Postgres — with a named volume held on external storage rather than the SD card. Two users, LAN-only exposure.
- The stack restarts on failure and starts at boot, so a power cut does not require someone to log in and bring it back.

**Operations**

- Scheduled off-device database dumps with rotating retention, integrity checks on every dump, loud failure notification, and a restore rehearsed before the household depends on the service.

**Testing**

- The repo currently has effectively one test. The store/availability filter is the correctness core of this change and needs direct test coverage, including the "no store means every store" rule and the availability-date boundary.

**Assumptions recorded**

- Two household members, both trusted; identity is a client-side selection, not a login.
- Quantities and units follow the existing prototype's unit set as a starting point.
- Item names are free text; no product catalogue or normalisation.
