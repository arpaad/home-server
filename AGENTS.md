# H.O.M.E. — notes for AI assistants

Context for working in this repository. For what the project is and how to
run it, read `README.md` first.

## Read the specs before changing behaviour

`openspec/` holds the specifications and the changes that implement them.
`openspec/changes/<change>/` contains a proposal (why), a design (the
decisions and what was rejected), delta specs (requirements and scenarios),
and tasks (the work, each with its own verification).

**A change to behaviour starts there, not in the code.** If you are about to
implement something the specs do not describe, say so and propose a change
rather than quietly widening one. If you find the spec is wrong, fix the spec
in the same commit as the code.

Tick a task only when its stated verification actually ran. An unticked task
is information; a falsely ticked one is a lie the next session will believe.

## Stack

- **Backend**: Python 3.14, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL.
  Managed with uv; the interpreter is pinned in `backend/.python-version`.
- **Frontend**: React 19 and TypeScript on Vite, TanStack Query, React
  Router (four routes, no nesting), a PWA service worker. Plain SPA —
  deliberately not Next.js, because the API serves the built files from its
  own origin and there is no server slot for a Node framework.
- **Toolchain**: mise pins node and uv (`mise.toml`).

## Layering, and the test that enforces it

```
api/         HTTP only — parses, calls a service, renders a response
service/     every business rule
repository/  persistence, behind Protocol interfaces
domain/      ORM-free types and invariants
dto/         wire representations
```

`backend/tests/test_layering.py` fails the build if a module under `api/`
imports a repository, or if anything under `domain/` imports SQLAlchemy. The
prototype's routes called repositories directly; that is how a rule ends up
duplicated across endpoints and how a client reaches the data by a path that
skips one.

## Code quality

- **Type safety**: pyright in **strict** mode, over `app/` and `tests/`.
  (Not mypy — an older note in this file said otherwise.)
- **Ruff** with a wide rule set, including `DTZ` (no naive datetimes), `TRY`
  (no long messages at a raise site — put them on the exception class), `S`,
  and `DOC` (docstrings must match signatures).
- **Tests against real infrastructure.** Backend tests use real PostgreSQL
  and build their schema by running the migrations. End-to-end tests drive a
  real browser against the real API — including with the network cut
  (`context.setOffline`) for the offline scenarios. Mocks that only agree
  with themselves prove nothing about the rules this project cares about.
- Comments explain *why*, especially where a decision looks arbitrary or a
  simpler-looking alternative is wrong.

## Rules this codebase exists to protect

Treat these as invariants, not preferences. Each one has tests.

1. **An item with no store belongs to every store.** This is what lets an
   item be written once instead of on two stores' lists, which is what
   stopped things being bought twice. It is expressed in SQL, once, in the
   repository — not in any client.
2. **Stores are referenced by foreign key, never by name.** A typo must not
   be able to invent a store and hide an item from the shop it belongs to.
   The client picks from existing stores and cannot submit free text.
3. **A purchase is an event row, not a flag.** An item is outstanding
   exactly when it has no purchase row. Marking one bought is idempotent.
4. **Availability is compared against the household's local date**, through
   `app/core/clock.py`. Evaluated in UTC, an item surfaces at 01:00 local,
   which is visible and wrong.
5. **Deleting a store that outstanding items reference is refused**, and the
   refusal names them. Unassigning instead would make a restricted item
   appear everywhere — the exact bug being fixed.
6. **A failed request is never shown as saved**, and cached list data is
   never presented as current.
7. **An item's category is its catalogue entry's, never its own.** Items
   have no `category_id`; they derive it through `catalogue_entry_id`.
   Correcting a category on the entry regroups every item, including ones
   already on the list. That is the whole point of "fix it once".
8. **The catalogue fills itself.** Every add finds or creates an entry by
   case-insensitive name, in the same transaction. A member never creates an
   entry by hand, and adding is never blocked by the catalogue.
9. **Suggestions are a prefix match, not fuzzy.** `mlik` must not silently
   match `milk`: the duplicate is what merge exists to surface. Remembered
   stores are a prefill the form always sends explicitly; the chips are the
   truth, never the catalogue.
10. **An item with no category is still shown**, in a final Uncategorised
    group. Grouping changes arrangement, never membership. The failure mode
    is silent, so it has its own end-to-end test.
11. **The service worker never serves API data.** It precaches the app
    shell only. The local copy is the persisted TanStack Query cache, in the
    layer that renders it — so the app *knows* whether what it shows is
    current, and says "last confirmed at …" when it is not. A worker-served
    response cannot say that.
12. **Every list operation is idempotent on replay.** Create carries a
    client id; edit carries `edited_at` and the server refuses an older one
    (later edit wins, answered `applied: false`, never an error); remove of
    a missing item is 204. Offline changes are paused mutations, persisted
    with the cache, resumed *in series* (one mutation scope) so "buy the item
    I just added" reaches the server after the add.
13. **A pending change is shown as pending, never as saved.** The mark comes
    from the mutation being in flight or paused, not from anything on the
    item. A permanent refusal (4xx other than 408/429) drops the mutation
    and pushes a notice; anything else keeps retrying.
14. **Clearing never deletes a purchase.** A bought item stays listed,
    dimmed, until the household clears it; clearing sets `cleared_at` on the
    item and leaves the purchase row exactly as recorded. The outstanding
    query is untouched by any of this — bought items come from a second
    query (`list_bought_uncleared`), so the correctness core's tests keep
    meaning what they meant.

## Security posture

This release **identifies** household members but does not authenticate
them. `get_current_member` is the single seam where that changes; it is
documented as trusting its caller absolutely. The service is LAN-only and
must not be exposed until the authentication change lands. Do not add
features that assume a trustworthy caller beyond what already exists, and do
not weaken that boundary for convenience.

## Working style

- Propose structural changes before making them; do not expand scope
  unasked.
- Prefer finishing and verifying one thing over scaffolding several.
- When something cannot be verified in the current environment, say so
  plainly and leave the task unticked rather than claiming it.
