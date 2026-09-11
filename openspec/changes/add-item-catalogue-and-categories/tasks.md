## 1. Prerequisite: give this change a base spec

- [x] 1.1 Sync `add-shopping-list`'s delta into `openspec/specs/shopping-list/spec.md`; verify `openspec validate add-item-catalogue-and-categories --strict` no longer reports "target spec does not exist" for the MODIFIED requirements

## 2. Schema and migration

- [ ] 2.1 Define the `CategoryORM` model — name unique case-insensitively, icon, colour, and a position for ordering; verify pyright passes and Alembic autogenerate produces a revision matching it
- [ ] 2.2 Define the `CatalogueEntryORM` model — name unique case-insensitively, nullable `category_id`, `last_used_at` — plus `catalogue_entry_stores` joining entries to stores; verify autogenerate matches the models
- [ ] 2.3 Add the nullable `shopping_items.catalogue_entry_id` foreign key, with `ON DELETE RESTRICT` so an entry in use cannot vanish; verify a test that deleting a referenced entry is refused by the database
- [ ] 2.4 Add an index on `lower(catalogue_entries.name)` supporting both the uniqueness rule and the prefix search; verify the suggestion query uses it via `EXPLAIN`
- [ ] 2.5 Write the migration including the backfill — one entry per distinct case-insensitive existing item name, every existing item linked to its entry, `last_used_at` from the newest item that used it; verify on a copy of the real database that every item ends up linked and no item's name, stores, dates or purchases changed
- [ ] 2.6 Verify the migration reverses: `alembic downgrade` drops the new tables and column and leaves `shopping_items` byte-identical to its pre-upgrade state on the same copy
- [ ] 2.7 Seed the default categories (produce, dairy, bakery, meat, frozen, household, drinks, other) with icons, colours and positions, idempotently like the member seed; verify running the seed twice leaves exactly one of each

## 3. Categories: domain, repository, service

- [ ] 3.1 Define the ORM-free `Category` domain type with its invariants — non-empty name, an icon, a colour; verify unit tests cover each rejection
- [ ] 3.2 Implement the category repository behind a `Protocol`, including case-insensitive name uniqueness; verify a test that adding "bakery" when "Bakery" exists is rejected and leaves one category
- [ ] 3.3 Implement listing categories in configured order and reordering them; verify a test that reordering changes the sequence returned and persists
- [ ] 3.4 Implement category removal that leaves referring catalogue entries uncategorised and reports how many were affected; verify a test that the count is right, the entries become uncategorised, and no item disappears from any list

## 4. Catalogue: domain, repository, service

- [ ] 4.1 Define the ORM-free `CatalogueEntry` domain type; verify pyright passes and a unit test constructs one with and without a category
- [ ] 4.2 Implement find-or-create by case-insensitive name, updating `last_used_at`; verify tests that a new name creates exactly one entry and that "Sourdough" reuses the entry for "sourdough" without creating a second
- [ ] 4.3 Implement the prefix suggestion query, ordered by `last_used_at` descending; verify tests for the spec's scenarios — "mil" offers "milk" and "mild cheddar" but not "bread", and the more recently used comes first
- [ ] 4.4 Implement setting an entry's category and its remembered stores, rejecting unknown stores as the item service already does; verify tests for both the update and the unknown-store rejection
- [ ] 4.5 Implement rename, refusing a name that collides with an existing entry; verify tests for the successful rename and for the refusal leaving both entries unchanged
- [ ] 4.6 Implement merge in one transaction — repoint every referring item, then delete the losing entry; verify tests that only the survivor remains, that every previously-referring item now points at it, and that a failure mid-way leaves neither entry changed
- [ ] 4.7 Implement removal that refuses while items refer to the entry and names them; verify tests for the refusal and for the successful removal of an unreferenced entry

## 5. Shopping list integration

- [ ] 5.1 Link every added item to a catalogue entry inside the same transaction as the item's creation; verify a test that adding an item creates the entry and links it, and that a rejected add (empty name, non-positive quantity) creates no entry
- [ ] 5.2 Copy the entry's remembered stores onto a new item as a prefill the caller may override; verify tests that the stores are copied, and that overriding them leaves the entry's remembered stores unchanged
- [ ] 5.3 Load each item's category through its catalogue entry in `list_outstanding`, as a join rather than a per-row lookup; verify the existing filter tests still pass unchanged and a test asserts the query count does not grow with the number of items
- [ ] 5.4 Order results by category position then item name, keeping the filter predicate untouched; verify every existing store-and-availability test passes with no edit to its assertions about *which* items appear
- [ ] 5.5 Verify by test that changing a catalogue entry's category regroups an item already on the list, with no edit to the item

## 6. API

- [ ] 6.1 Add category endpoints — list, create, update, reorder, delete — with the delete reporting how many entries become uncategorised; verify contract tests for the ordering and for the delete report
- [ ] 6.2 Add catalogue endpoints — list, update, rename, merge, delete — mapping the refusals to their status codes through the existing error handler table; verify contract tests for rename collision (rejected) and merge (items repointed)
- [ ] 6.3 Add the suggestion endpoint taking a name prefix; verify a contract test covering the spec's ordering and matching scenarios
- [ ] 6.4 Extend the item representation with its catalogue entry and derived category; verify a contract test that an item whose entry is uncategorised reports no category rather than failing
- [ ] 6.5 Verify the layering test still passes — no module under `api/` imports a repository, and nothing new under `domain/` imports SQLAlchemy

## 7. Client: routing and the read-first main screen

- [ ] 7.1 Add a router with `/`, `/add`, `/manage` and `/catalogue`; verify each route survives a full page reload when served by the API container, not only by the dev server
- [ ] 7.2 Reduce the main screen to the list, the store filter and an add control, removing the inline form; verify an end-to-end test that no item entry form is present on `/`
- [ ] 7.3 Move adding onto `/add`, returning to the list on both add and cancel; verify an end-to-end test covering both paths
- [ ] 7.4 Verify by end-to-end test that the system back gesture leaves `/add` and returns to the list, rather than leaving the app

## 8. Client: categories, catalogue and grouping

- [ ] 8.1 Render the list grouped by category with each group's icon, colour and name, in configured order; verify an end-to-end test that groups appear in the configured order for a store-filtered view
- [ ] 8.2 Render an uncategorised group for items whose entry has no category; verify an end-to-end test that a freshly typed item is visible under it rather than absent — the failure here is silent, so this test is the guard
- [ ] 8.3 Build the typeahead on the add page, debounced and never blocking the add button; verify an end-to-end test that a name matching nothing can still be added while a suggestion request is outstanding
- [ ] 8.4 Apply a chosen suggestion's category and remembered stores as an editable prefill; verify the spec's scenario end to end — choosing "ketchup" prefills Lidl and Spar, clearing them adds an unrestricted item, and the entry still remembers both
- [ ] 8.5 Build the stores and categories management page, including reordering categories and choosing an emoji icon and colour; verify by end-to-end test that a reorder changes the grouping on the list
- [ ] 8.6 Build the catalogue management page — set category and stores, rename, merge, delete; verify an end-to-end test of the correct-it-later flow: type a new name in a hurry, categorise it afterwards, and see the next add of that name carry the category
- [ ] 8.7 Verify by end-to-end test that a rename collision offers merging rather than silently failing

## 9. Acceptance

- [ ] 9.1 Rehearse the migration against a dump of the live household database, take a fresh dump first, then apply it; verify the item count, every item's stores, and every recorded purchase are identical before and after
- [ ] 9.2 Walk through every scenario in this change's three spec files against the deployed stack on a phone; verify each behaves as specified and record any that do not
- [ ] 9.3 Confirm the shopping flow is faster for a repeat item than before the change, by adding the same five items twice — once cold, once from suggestions — and comparing the number of taps
- [ ] 9.4 Update `README.md` and `AGENTS.md` for categories, the catalogue and the new screens, adding the catalogue-and-category rules to the list of invariants the codebase protects; verify the documented flows match what the app does
