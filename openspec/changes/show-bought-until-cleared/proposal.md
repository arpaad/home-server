## Why

Ticking an item off makes it vanish. In a shop that is disorienting: a wrong tap — and rows are tap targets, held one-handed — leaves no trace of what just disappeared, and the only way back is an undo banner that goes away by itself. There is also no way to look down at the end of the trip and see what has been picked up, which is the check everyone does before the checkout.

The fix is to let a bought item stay where it can be seen, greyed and at the bottom, until someone deliberately clears the bought ones away.

## What Changes

- **A bought item stays visible**, dimmed and grouped at the bottom of the list, in every view it would otherwise have appeared in. It is unmistakably done, and it is still there to check and to undo.

- **Undo is on the row.** Tapping a dimmed item's tick returns it to the outstanding list. The transient undo banner goes; the row is the undo.

- **A "clear bought" control** at the top of the list takes every bought item out of view in one action. It marks them cleared; it does not delete them. Their purchase records stay, because they are what a later purchase history and the finance module attach to, and a clear-away button must not be the thing that destroys them.

- **Cleared is a new state, not a new meaning for bought.** An item is *outstanding* (no purchase), *bought* (a purchase, not cleared) or *cleared* (a purchase, and cleared). Only the last is hidden. This needs one nullable column.

- Bought items are shown regardless of availability date, since availability is about whether to buy something and they already were.

### Out of Scope

- **Automatic clearing** after a day or a week. Chosen deliberately: items stay until someone clears them, so the list is predictable and today's shopping can be reviewed at leisure. If they pile up in practice, a time-based sweep is an easy later change.
- **A purchase history view.** The records are kept; browsing them is a different change.
- **Un-clearing.** A cleared item is done. If it is needed again it is added again, and the catalogue makes that cheap.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `shopping-list`: **Marking an item as bought** no longer removes the item from view; it moves it to a dimmed bought group. **Undoing a purchase** happens from that group. **Store-filtered shopping view** and **Full list view** include the bought group. A new requirement, **Clearing bought items**, covers the control that hides them.

> **Layering note.** `add-item-catalogue-and-categories` also modifies the two view requirements (to add grouping) and is not yet archived. This change's delta is written against the text *as that change leaves it*, and must be archived after it.

## Impact

**Affected code**

- `backend/app/modules/shopping/repository/orm.py` — `shopping_items.cleared_at`, nullable timestamp.
- `backend/app/modules/shopping/repository/item_repository.py` — a second query for bought-but-not-cleared items, alongside the outstanding query, which stays exactly as it is.
- `backend/app/modules/shopping/service/shopping_list_service.py` — the views return outstanding then bought; `clear_bought`; undo also un-clears.
- `backend/app/modules/shopping/api/routes.py` — the item representation gains `cleared_at`; a `clear-bought` endpoint.
- `frontend/src/pages/ListPage.tsx`, `GroupedList.tsx`, `ItemRow.tsx` — the bought group, the row-tap undo, the clear control.
- New Alembic migration: add the column, no backfill needed (existing bought items become visible-but-bought, which is the new intended state).

**Data**

- One column, nullable, no backfill. Reversible by dropping it.

**Assumptions recorded**

- "Clear bought" clears every bought item across all stores, not only those in the current view. A shopping trip is over when it is over.
- Within the bought group, the most recently bought item comes first, so the thing just ticked sits right under the line.
- A bought item's stores still decide which store views it appears in, exactly as they did while it was outstanding.
