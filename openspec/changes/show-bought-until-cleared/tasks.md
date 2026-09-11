## 1. Schema

- [ ] 1.1 Add the nullable `shopping_items.cleared_at` timestamp to the ORM and generate the migration with no backfill; verify autogenerate matches the model, and that upgrade then downgrade leaves `shopping_items` byte-identical on a copy of the database

## 2. Domain and repository

- [ ] 2.1 Add `cleared_at` to the domain item and an `is_cleared` property; verify a unit test that a bought-and-cleared item is not outstanding and is cleared
- [ ] 2.2 Implement `list_bought_uncleared(store_id)` — items with a purchase and no `cleared_at`, filtered by store on the "no store means every store" terms, ignoring availability, most recently bought first; verify tests for each of those four properties, and that every existing `list_outstanding` test passes with no edit to its assertions
- [ ] 2.3 Implement `clear_bought()` setting `cleared_at` on every bought-uncleared item and returning the count; verify a test that it clears only those, is idempotent, and leaves every purchase row in place
- [ ] 2.4 Make `remove_purchase` also reset `cleared_at`; verify a test that undoing a cleared item leaves it outstanding and uncleared

## 3. Service and API

- [ ] 3.1 Make the shopping view and the full list return outstanding items followed by bought-uncleared ones; verify tests that the order is outstanding-then-bought, that a cleared item is absent, and that a bought item assigned only to Aldi is absent from Lidl's view
- [ ] 3.2 Add `clear_bought` to the service and a `POST /api/shopping/items/clear-bought` endpoint returning the count; verify a contract test that three bought and two outstanding items yield a count of three, the outstanding two are unchanged, and the purchases still exist
- [ ] 3.3 Add `cleared_at` to the item representation; verify a contract test that a bought item lists with a purchase and null `cleared_at`, and that after clearing it is not listed

## 4. Client

- [ ] 4.1 Split bought items into a final "Bought" group after every category group, dimmed, most recently bought first; verify an end-to-end test that ticking an item moves it below every outstanding item with a bought appearance, in both the store view and the full list
- [ ] 4.2 Make the tick on a bought row perform the undo and remove the undo banner; verify an end-to-end test that tapping the tick on a bought item returns it to its category group
- [ ] 4.3 Add a "Clear bought (N)" control at the top of the list, hidden or disabled when N is zero; verify an end-to-end test that it removes every bought item from the Lidl view *and* the Spar view, and that the count shown matched what was cleared
- [ ] 4.4 Verify by end-to-end test that the spec's ketchup scenario still holds — ketchup bought in Lidl shows as bought in Spar, and is not among the outstanding items anywhere

## 5. Acceptance

- [ ] 5.1 Update `README.md` and `AGENTS.md`: the bought group, clearing, and the invariant that clearing never deletes a purchase; verify the documented flow matches the app
- [ ] 5.2 Walk the modified scenarios on a phone; note that historical bought items appear in the bought group after the first deploy and clear them once
