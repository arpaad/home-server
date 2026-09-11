## Context

See `proposal.md` — Why. This section covers only the state of the system that shapes the approach.

What exists today, after `add-shopping-list`:

- `shopping_items` holds a free-text `name`, quantity, unit, an optional `available_from`, an `origin`, and links to `stores` through `shopping_item_stores`. A purchase is a row in `shopping_item_purchases`, so an item is outstanding exactly when it has none.
- The store-and-availability filter is one SQL predicate in `SqlAlchemyShoppingItemRepository.list_outstanding`. It is the correctness core of the product and is covered by tests against real PostgreSQL.
- Layering is `api → service → repository → domain`, enforced by `backend/tests/test_layering.py`: no module under `api/` may import a repository, and nothing under `domain/` may import SQLAlchemy.
- The client is a single-screen React app with **no router**. `App.tsx` holds the list, the filter chips and the add form together, with state in `useState` and server data behind TanStack Query.
- Ruff runs `DTZ` (no naive clocks), `TRY` (no long messages at raise sites) and `DOC`; pyright runs strict over `app/` and `tests/`.
- There is real household data. Unlike the previous change, this one cannot say "nothing depends on it yet".

The previous change recorded the opposite of this one: *"Item names are free text; no product catalogue or normalisation."* That was right when nothing had been typed twice. It is wrong now, and this change reverses it deliberately rather than by drift.

**Base-spec dependency.** `openspec/specs/` is empty; `shopping-list` exists only as a delta inside the unarchived `add-shopping-list`. `openspec validate --strict` already reports that archiving this change's `MODIFIED` requirements would fail for want of a target spec. Syncing `add-shopping-list` into `openspec/specs/` is therefore a prerequisite task here, not an afterthought.

## Goals / Non-Goals

**Goals:**

- Make the common case — re-adding something bought before — cost a few keystrokes and no decisions.
- Keep the correctness core intact: adding grouping must not change *which* items a store's view contains.
- Keep the catalogue self-maintaining, and give it the one repair operation (merge) without which it rots.
- Introduce routing to the client without turning a one-screen app into a framework.

**Non-Goals:**

- Per-store aisle ordering. One household-wide category order.
- Any inference: no guessing a category from a name, no fuzzy matching beyond a prefix.
- Reworking the existing store or purchase model. Both stay exactly as they are.

## Decisions

### A catalogue entry is a first-class row, not derived from item history

`catalogue_entries` is its own table. `shopping_items` gains a nullable `catalogue_entry_id`.

**Chosen because** the entry must be *editable* — "later I will change its category in that page" only means something if there is one durable row to change. Deriving suggestions from past `shopping_items` rows would make "set milk's category" an update of every historical row, or of an arbitrarily chosen one, and would lose the correction as soon as those rows aged out.

**Alternatives considered.** *Suggest from a `DISTINCT name` query over `shopping_items`*: no schema change and suggestions work immediately, but there is nowhere to hang a category, nowhere to record a merge, and a typo is unfixable. *A full product model with brands and packaging*: solves problems this household does not have.

The column is **nullable** rather than mandatory so that the migration cannot fail on data it does not understand; the backfill fills it, and the code treats a null entry as uncategorised rather than as an error.

### Category lives on the catalogue entry only, never copied onto the item

An item has no `category_id`. Its category is read through `catalogue_entry → category`.

**Chosen because** it is the only shape in which correcting a category is genuinely a single action, which is what was asked for. Copying the category onto the item at add-time would leave the item already on the list showing the old grouping, and the same product sitting in two groups across two weeks.

**Trade-off, stated plainly:** a member cannot say "this once, put this under Bakery instead". That override is a real loss. It is accepted because the alternative — two sources of truth for one item's category — produces confusing groupings far more often than the override would be wanted, and because the correction path (edit the entry) is one tap from the item.

**Alternatives considered.** *Copy on add, with the entry as a template*: allows per-item override, rejected above. *Copy on add but re-sync on entry edit*: the worst of both — it looks like an override until something silently overwrites it.

### Remembered stores are a prefill, and the item still owns its own

The entry holds remembered stores in `catalogue_entry_stores`; adding an item copies them onto the item's own `shopping_item_stores`, after which the two are independent.

**Chosen because** stores are unlike category here. Category answers "what kind of thing is this", which is a property of the thing and should be shared. Stores answer "where should we get it this time", which genuinely varies — the deciding case is "we normally get ketchup at Lidl, but we are in Spar now". Copying preserves the existing store model completely: `list_outstanding` keeps working on `shopping_item_stores` and needs no change at all.

**Alternatives considered.** *Derive stores from the entry like category*: would force the filter query through another join and make "just this once" impossible. *Do not remember stores*: rejected — re-picking the same two chips weekly is exactly the tedium this change targets.

### Grouping happens in the client; the query keeps returning a flat, ordered list

The repository returns items with their category loaded, ordered by category position then item name. The client splits that into groups.

**Chosen because** the filter predicate is the part of this system most expensive to get wrong, and it already has thorough tests. Grouping is presentation: it changes arrangement, never membership. Keeping the query flat means the predicate is untouched and the existing tests keep meaning what they meant.

The category is loaded with the items (a join, not a per-row lookup) so grouping costs no extra queries. At a few dozen rows this is not a performance decision — it is about not making the grouping code able to drop a row.

**Alternatives considered.** *`GROUP BY` in SQL returning nested structures*: pushes presentation into the layer that must stay simple. *Fetch categories separately and zip client-side*: an N+1 in disguise and a chance to lose items with no category.

### Suggestions use a prefix match in PostgreSQL, with no search extension

`WHERE lower(name) LIKE lower(:prefix) || '%'`, ordered by `last_used_at DESC`, backed by an index on `lower(name)`.

**Chosen because** the catalogue will hold a few hundred rows at the outside. Trigram similarity, full-text search or a fuzzy-matching library would all work and all cost a dependency, an extension or an index to explain, for a table small enough to scan. Prefix matching is also what the interaction implies: a member types the start of a word.

`last_used_at` is denormalised onto the entry rather than derived from the newest referencing item, because ordering suggestions is the single hottest read in the feature and it should not require an aggregate over items on every keystroke.

**Alternatives considered.** *`pg_trgm` for typo tolerance*: attractive, but it makes "mlik" match "milk" and thereby hides the duplicate the merge feature exists to surface. *Client-side filtering of the whole catalogue*: viable at this size, rejected because it would put the matching rule in the client where a second client could disagree with it.

### Merge is an operation, not a delete-and-retype

Merging repoints every `shopping_items.catalogue_entry_id` from the losing entry to the surviving one inside one transaction, then deletes the loser.

**Chosen because** a duplicate entry usually already has history behind it. Deleting it would either orphan those items or be refused, and retyping them is exactly the work this change removes. One transaction, because a half-merged catalogue is worse than a duplicated one.

### The client gets a router, with four routes and no more

`/` (the list), `/add`, `/manage` (stores and categories), `/catalogue`.

**Chosen because** the read-first main screen requires that adding be somewhere else, and "somewhere else" needs an address — a reloaded page or an installed PWA reopening must land where it was. The API already serves the client's entry document for any non-API path, so client-side routes reload correctly; that behaviour is tested.

**Alternatives considered.** *Modal overlays with no routing*: no new dependency, but a modal cannot be reopened by a reload, cannot be backed out of with the system back gesture, and on a phone the back gesture is how people close things. *A full app framework*: rejected in `add-shopping-list` and rejected again for the same reasons.

### Categories are seeded, and seeded ones are ordinary

The seed inserts a default set on an empty database, exactly as household members are seeded. They carry no protected flag.

**Chosen because** an empty category list makes the feature look broken on first use, and a set of "system" categories that cannot be renamed would collide with the household's own words for things within a week.

## Risks / Trade-offs

- **The migration touches live household data** → It backfills a catalogue entry per distinct item name and links existing items to it. It must be reversible, rehearsed against a copy of the real database, and taken with a dump in hand. This is the first migration in this project that can lose something real.

- **Per-item category override is impossible** → Accepted, and stated in the decision above. If it turns out to be wanted often, the fix is a nullable `category_id` override on the item, which this schema can take later without a data loss.

- **The catalogue accumulates near-duplicates** → Rename and merge exist for exactly this, and prefix matching keeps duplicates *visible* rather than silently unifying them. The management page is where this is cleaned up; if it is never opened, suggestions degrade slowly rather than breaking.

- **Grouping could hide items** → The uncategorised group is a requirement, not a fallback, and has its own scenarios. The client must render a group for items with no category rather than filtering them out — the failure mode is silent, so it gets a test.

- **A router is a new client dependency and a new way to get lost** → Four routes, no nesting, no guards. The main screen remains the default and every other route returns to it.

- **Typing latency on a phone** → Suggestions are requested as the member types. Debounced, and never blocking: the add button stays usable while a request is in flight, because the spec requires that an unfamiliar name can always be added.

- **Two members editing the catalogue at once** → Last write wins, as elsewhere in this project. At two users the coordination cost of anything better exceeds the cost of the rare conflict.

## Migration Plan

1. **Sync `add-shopping-list` into `openspec/specs/`** so this change's `MODIFIED` requirements have a base spec. Without this, archiving fails — `openspec validate --strict` already says so.
2. Add `categories` and `catalogue_entries`, seed the default categories, and add the nullable `shopping_items.catalogue_entry_id`.
3. Backfill: one catalogue entry per distinct case-insensitive item name, every item linked to its entry, `last_used_at` taken from the newest item that used it. Existing items keep their own stores untouched; entries start with no remembered stores rather than guessed ones.
4. Build the backend behind the existing layering, with the filter query unchanged except for loading the category.
5. Introduce the router and split the screens, then add grouping, then the typeahead.
6. Rehearse the migration against a dump of the live database before applying it there.

**Rollback:** the migration's `downgrade` drops the new tables and the column, leaving `shopping_items` exactly as before — every item keeps its name, stores, dates and purchases, since none of those move. A dump taken before the upgrade covers the case where the backfill itself was wrong.

## Open Questions

- Whether category order should eventually vary per store, to match one shop's aisles. Deferred deliberately: one order has to prove insufficient first, and the schema can carry a per-store ordering later without disturbing anything decided here.
- Whether a future recipe module should create catalogue entries directly. The `origin` field already distinguishes manual from recipe items, so this can be answered when that module exists.
