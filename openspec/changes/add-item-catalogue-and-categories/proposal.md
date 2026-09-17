## Why

The list works, but adding to it is slow and the result is unsorted. The same twenty-odd things are bought week after week, and each one is retyped from scratch, its stores re-picked every time. Nothing remembers that milk was bought last Tuesday, or that ketchup always comes from Lidl or Spar.

The list is also flat. In a shop that means walking the aisles in whatever order items happened to be typed, and doubling back for the yoghurt because it sat between the washing powder and the light bulbs.

Finally, the client is shaped for the wrong task. The add form is permanently on screen, directly under a list whose rows are tap targets — but the overwhelmingly common action in a shop is *taking things off* the list, not putting them on. The most-used screen is optimised for the least-used action, and the add form is a mis-tap surface exactly when hands are full.

## What Changes

- **Categories become a first-class entity**, each with a name, an emoji icon and a colour. A set is seeded (produce, dairy, bakery, meat, frozen, household, drinks, other) and members can add, rename, recolour and delete their own.

- **An item catalogue remembers what the household buys.** Adding an item records its name in the catalogue, so typing it next time offers a suggestion. Choosing a suggestion carries the remembered category and stores across as a prefill.

- **The catalogue is filled by using the list, not by maintaining it.** Typing a new name adds a catalogue entry automatically. Correcting its category later is a separate, unhurried action on the catalogue page — the point is to type fast in the moment and get the benefit next week.

- **Category is owned by the catalogue entry, and list items derive it.** Correcting a category regroups the current list immediately, so "fix it once" means once. **BREAKING** for the item representation: an item's category is read through its catalogue entry rather than stored on the item.

- **The shopping views group by category**, in a configurable order, with an explicit *Uncategorised* group so a freshly typed item is never hidden.

- **The client gains two management pages**: one for stores and categories, one for the catalogue. Both are for tidying up at home, not for use in a shop.

- **The main screen becomes read-first.** It shows the list and the store filter. Adding moves behind a `+` button onto its own page, so the screen used while walking around a shop contains only the actions wanted there.

- **The catalogue can be tidied**: entries can be renamed and merged. Without this it accumulates every typo forever, and a suggestion list full of `mlik` is worse than no suggestions at all.

- **A starter pack ships with the app**: thirty Hungarian categories and some seven hundred everyday items, food and household alike, each categorised, so suggestions are useful from day one. It is inserted once into an empty database and then belongs to the household — what they rename or remove stays that way. (The previous seed re-inserted "missing" defaults on every start, which resurrected deliberate deletions; that is fixed here.)

- **A category can be chosen where an item is added or edited**, not only on the catalogue page. The choice is recorded on the item's catalogue entry — the item still owns no category of its own — so it applies to every item of that name, and the form says so. The catalogue page also gains a way to add an entry directly, with a category and stores, without putting anything on the list.

### Out of Scope

- **Aisle ordering per store.** Category order is one household-wide sequence, not a different one per shop. A per-store aisle map is a plausible later change; it is not worth its complexity until the single ordering proves insufficient.
- **A shared product database or barcode scanning.** The catalogue holds what this household has actually typed, nothing more.
- **Automatic categorisation.** No guessing a category from a name; a member sets it, once.
- **Quantity and unit memory.** The catalogue remembers category and stores. How much is needed genuinely varies week to week.
- **Authentication**, still. Unchanged from the previous release, and still the gate on exposing this beyond the LAN.

## Capabilities

### New Capabilities

- `shopping-categories`: Categories that group items in the shopping views — their registry, their appearance (icon and colour), their household-wide ordering, and the rules protecting a category that items still rely on.
- `item-catalogue`: The household's memory of what it buys. Covers how entries come to exist, how suggestions are offered while typing, what a suggestion carries across, and how entries are corrected, renamed and merged.

### Modified Capabilities

- `shopping-list`: **Adding an item** gains an optional catalogue reference, and an item's category is derived from it. **Store-filtered shopping view** and **Full list view** gain grouping by category. A new requirement covers the read-first main screen and the separate add page.

> **Dependency, recorded deliberately.** `openspec/specs/` is currently empty: the `shopping-list` capability exists only as a delta inside the unarchived `add-shopping-list` change. This change's delta assumes that base spec. `add-shopping-list` must be synced into `openspec/specs/` (or archived) before this change is archived, or the two deltas will not layer onto anything.

## Impact

**Affected code**

- `backend/app/modules/shopping/domain/` — new `Category` and `CatalogueEntry` types; `ShoppingItem` gains a catalogue reference and a derived category.
- `backend/app/modules/shopping/repository/orm.py` — new `categories` and `catalogue_entries` tables, plus a join table for a catalogue entry's remembered stores; `shopping_items` gains a nullable `catalogue_entry_id`.
- `backend/app/modules/shopping/repository/item_repository.py` — the store-and-availability query must now also load the category for grouping, without becoming N+1.
- `backend/app/modules/shopping/service/` — a catalogue service (create-on-add, suggest, rename, merge) and a category service.
- `backend/app/modules/shopping/api/routes.py` — endpoints for categories, catalogue entries and suggestions.
- New Alembic migration. It must **backfill a catalogue entry for every existing item** so nothing on the current list loses its identity.
- `frontend/src/` — a router (there is none today), the new add page, the two management pages, category grouping in the list, and a typeahead.
- `frontend/e2e/` — the suggestion-carries-category flow and the group-by-category rendering are the two things most worth proving in a browser.

**Dependencies**

- Frontend: a router. Everything else already present.
- Backend: none. Suggestion matching uses PostgreSQL's own prefix matching; the catalogue is a few hundred rows at most, and reaching for a search extension at this size would be unjustified.

**Data**

- One migration, with a backfill. There is real household data by now, so the migration must be reversible and rehearsed rather than assumed.

**Assumptions recorded**

- Two members, one household, one shared list — unchanged.
- Suggestions match on a prefix of the item name, case-insensitively, and are ordered by how recently the entry was used.
- Deleting a category leaves its catalogue entries uncategorised rather than refusing, because unlike a store assignment, an absent category hides nothing — it only moves rows into *Uncategorised*.
- A catalogue entry is never hard-deleted while items reference it; merging is the way to remove a duplicate.
