## 1. Repository restructure

- [ ] 1.1 Move `app/`, `tests/` and the Python project files into `backend/`, and create the `frontend/` and `deploy/` directories, leaving the `Makefile`, `README.md`, `AGENTS.md` and `openspec/` at the root; verify `uv sync` and the existing test suite still run from the new location
- [ ] 1.2 Repoint `pyproject.toml` package discovery and `pyrightconfig.json` at the new layout; verify pyright reports no errors
- [ ] 1.3 Repoint every Makefile target at `backend/`, keeping the Makefile at the repository root; verify `make lint-all` and `make test` succeed exactly as before
- [ ] 1.4 Repoint the pre-commit hook that filters on `app/`; verify `pre-commit run --all-files` passes
- [ ] 1.5 Move the container definition into `deploy/` and repoint its copy paths; verify `make build` still produces a runnable image
- [ ] 1.6 Update both GitHub Actions workflows for the new paths and add path filters so a client-only change does not run pyright; verify the workflow run is green

## 2. Project foundations

- [ ] 2.1 Populate the empty `core/config.py` with typed settings (database URL, household timezone, environment) loaded from the environment; verify the app starts with settings injected and pyright reports no errors
- [ ] 2.2 Add the Postgres driver, settings and Alembic dependencies through uv; verify `uv sync` succeeds and `uv.lock` is updated
- [ ] 2.3 Point `db/session.py` at Postgres via settings and remove the import-time `init_tables()` call; verify importing the module creates no tables
- [ ] 2.4 Write the compose definition with an API service and a Postgres service, a health check on the database, the API depending on it being healthy, restart policies on both, a named volume, and binding to the LAN interface only; verify both start, the API serves its OpenAPI docs, and restarting the API container loses no data
- [ ] 2.5 Initialise Alembic against the configured database URL; verify migrating to head succeeds against the compose Postgres
- [ ] 2.6 Add the Makefile database targets — `db-up`, `db-down`, `db-reset`, `migrate`, `migration`, `seed`, `up`, `down`, `logs`; verify `make db-reset` produces a migrated and seeded database starting from nothing
- [ ] 2.7 Make the API container entrypoint migrate to head before starting the server; verify a fresh container against an empty database ends up fully migrated with no manual step

## 3. Domain model and schema

- [ ] 3.1 Define ORM-free domain types for household member, store, shopping item and purchase; verify pyright passes and a unit test constructs each
- [ ] 3.2 Enforce the item invariants in the domain — non-empty name, quantity greater than zero; verify unit tests cover both rejections from the "Adding an item" scenarios
- [ ] 3.3 Define ORM models: `stores` with a case-insensitively unique name, `shopping_items` with `available_from` and origin, `shopping_item_stores` as a join table with foreign keys, `shopping_item_purchases`, and `household_members`; verify Alembic autogenerate produces a revision matching them
- [ ] 3.4 Write and apply the initial migration; verify migrating to head and back down to base both succeed
- [ ] 3.5 Seed the two household members; verify they are readable after a fresh migration on an empty database

## 4. Repository layer

- [ ] 4.1 Declare `Protocol` repository interfaces for items and stores; verify pyright accepts the SQLAlchemy implementations as satisfying them
- [ ] 4.2 Implement the store repository including case-insensitive name uniqueness; verify a test that adding "lidl" when "Lidl" exists is rejected and leaves one store
- [ ] 4.3 Implement the store-and-availability filter as a single SQL query in the item repository; verify tests that an item with no stores appears for every store, an item restricted to Lidl and Spar appears for neither Aldi nor Auchan, an item with a future `available_from` is excluded, and a purchased item is excluded
- [ ] 4.4 Compute "today" for the availability comparison in the configured household timezone, never from a naive clock; verify a test at the date boundary and that ruff's `DTZ` rules pass
- [ ] 4.5 Implement the lookup for outstanding items referencing a given store; verify a test returns exactly the referencing items

## 5. Service layer

- [ ] 5.1 Implement the shopping list service for adding, editing and removing items, rejecting references to stores that do not exist; verify tests for the unknown-store rejection and that removal records no purchase
- [ ] 5.2 Implement marking an item bought and undoing it, with marking made idempotent; verify tests that a second mark does not create a second purchase and that undo leaves no purchase recorded
- [ ] 5.3 Implement store creation and deletion, refusing deletion while outstanding items reference the store and reporting those items; verify tests for both the refusal and the successful deletion of an unused store
- [ ] 5.4 Move all business rules out of the API layer so routes call services only; verify a test asserting that no module under `api/` imports anything from `repository/`

## 6. API layer

- [ ] 6.1 Add a single `get_current_member` dependency resolving the acting member, documented as trusting its caller until the authentication change; verify a test that a missing or unknown member is rejected
- [ ] 6.2 Implement the item endpoints — list with optional store filter and upcoming inclusion, create returning the created item, patch, delete; verify contract tests covering the "Store-filtered shopping view" and "Full list view" scenarios
- [ ] 6.3 Implement purchase and undo as sub-resources of an item; verify a contract test that buying an item assigned to both Lidl and Spar removes it from both views
- [ ] 6.4 Implement the store endpoints, returning a conflict naming the referencing items when a store in use is deleted; verify a contract test for that response
- [ ] 6.5 Implement the household members endpoint; verify it returns the seeded members
- [ ] 6.6 Register the new router and delete the prototype shopping module and its `/shopping-items` routes; verify the old path returns 404 and the whole test suite passes
- [ ] 6.7 Serve the built client from the API, returning the client's entry document for non-API paths; verify that reloading the page on a client-side route returns the app rather than a 404

## 7. Progressive web client

- [ ] 7.1 Scaffold a React and TypeScript workspace under `frontend/` with a production build; verify the build produces servable static assets
- [ ] 7.2 Build the API client with a query cache exposing explicit loading and error states; verify a test that a failed request surfaces an error rather than a silent empty list
- [ ] 7.3 Implement member selection persisted on the device; verify that a purchase made from the client is attributed to the selected member
- [ ] 7.4 Implement the full list view showing each item's stores and availability date; verify against the "Reviewing the whole list at home" scenario
- [ ] 7.5 Implement the store-filtered shopping view; verify the ketchup case end to end — ketchup assigned to Lidl and Spar and an unassigned milk both appear under Lidl, while an Aldi-only item does not
- [ ] 7.6 Implement the add and edit form with store selection restricted to existing stores as chips and adding a new store as a separate deliberate action; verify no code path submits a free-text store name
- [ ] 7.7 Implement marking bought and undoing it; verify the item disappears from every store's view immediately and returns on undo
- [ ] 7.8 Add the web app manifest and a service worker that precaches the application shell only and never serves cached list data as current; verify installation to a phone home screen and that data requests reach the network

## 8. Deployment, durability and acceptance

- [ ] 8.1 Build a multi-stage image in which Node builds the client and the Python runtime image serves both it and the API; verify one image runs the API and serves the client
- [ ] 8.2 Build arm64 images in CI so the Pi pulls rather than builds; verify the published image runs on the Pi
- [ ] 8.3 Place the database volume on external storage rather than the SD card; verify the volume's backing path is on the external device
- [ ] 8.4 Add systemd units so the stack starts at boot; verify by power-cycling the Pi that the list loads afterwards with no manual step
- [ ] 8.5 Add a systemd timer taking compressed dumps with hourly, daily and monthly retention; verify dumps accumulate on schedule and that expired ones are pruned
- [ ] 8.6 Verify each dump's integrity by listing its contents and fail loudly to a notification on error; verify by deliberately breaking the job that the notification actually arrives
- [ ] 8.7 Copy every dump off the device to a separate machine; verify a dump written on the Pi appears on the target
- [ ] 8.8 Perform a restore drill into an empty database; verify the restored list, stores and purchases match the source
- [ ] 8.9 Walk through every scenario in `specs/shopping-list/spec.md` against the deployment on the Pi using both phones; verify each scenario behaves as specified and record any that do not
- [ ] 8.10 Update `README.md` and `AGENTS.md` for the new repository layout, Postgres, the migration workflow, the Makefile database targets and the backup and restore procedure, stating that the service is LAN-only and must not be exposed until authentication exists, and pointing at `openspec/` as the place where specifications and changes live; verify the documented setup steps work from a clean checkout
