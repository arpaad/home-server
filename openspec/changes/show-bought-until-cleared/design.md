## Context

See `proposal.md` — Why. What shapes the approach:

- A purchase is already an event row in `shopping_item_purchases`; an item is outstanding exactly when it has none. Nothing about that changes.
- `SqlAlchemyShoppingItemRepository.list_outstanding` holds the store-and-availability predicate, the correctness core of the product, with tests against real PostgreSQL that assert exactly which items appear. Those tests must keep passing with no edit to their assertions.
- The client groups a flat, ordered list in one pass (`grouping.ts`) and renders it in `GroupedList`. `ItemRow`'s tick is a button that is disabled once bought.
- The two view requirements are also modified by `add-item-catalogue-and-categories`, which is not yet archived.

## Goals / Non-Goals

**Goals:**

- Bought items visible, dimmed, at the bottom, until cleared — and undoable from the row.
- Zero change to the outstanding predicate or its tests.
- Purchase records survive clearing.

**Non-Goals:**

- Time-based automatic clearing.
- Any purchase-history browsing.
- Per-store clearing.

## Decisions

### `cleared_at` on the item, not a flag on the purchase

A nullable `shopping_items.cleared_at` timestamp.

**Chosen because** clearing is something that happens to the item's place on the list, not to the purchase. A purchase is a fact about the world ("bought, by whom, when") and should stay exactly as recorded; whether the household has finished looking at the row is a separate concern. A timestamp rather than a boolean, because "when was this cleared" is free to record now and impossible to reconstruct later.

**Alternatives considered.** *Delete the item on clear*: destroys the purchase row by cascade — the exact history the previous change kept on purpose. *A `cleared` boolean on the purchase*: mixes two concerns and would need to move if purchases ever become many-per-item. *No column, hide bought items older than N hours*: no state to reason about, but the household explicitly asked for items to stay until cleared.

### A second query, not a widened one

`list_outstanding` stays byte-for-byte as it is. A new `list_bought_uncleared(store_id)` returns items with a purchase and `cleared_at IS NULL`, filtered by store on the same "no store means every store" terms, ordered by `bought_at DESC`. The service returns outstanding followed by bought.

**Chosen because** the outstanding predicate is the thing most expensive to get wrong, and it has thorough tests whose assertions say precisely which items appear. Widening it to `OR (bought AND uncleared)` would change what every one of those tests observes. Two queries at a few dozen rows costs nothing measurable and keeps the important one untouched.

The bought query deliberately ignores `available_from`: availability is about whether to buy something, and a bought item already was.

### Bought is its own group, after everything, not a dimmed row inside its category

The client appends one "Bought" group after the last category group.

**Chosen because** the household asked for bought items at the bottom, and because a bought row sitting greyed inside Dairy would still be scanned while looking for what is left to get. At the bottom it is out of the way of the shopping and in the way of the review, which is the right order.

Ordering within the group is most recently bought first, so the item just ticked sits right under the line and an accidental tick is the nearest thing to undo.

### The row is the undo; the banner goes

The tick on a bought row is enabled and performs the undo. The transient undo banner is removed.

**Chosen because** the banner was the workaround for items vanishing. With the item still visible, a second affordance for the same action is clutter, and one that disappears on its own is a worse one.

### Clear is household-wide and does not delete

`POST /api/shopping/items/clear-bought` sets `cleared_at = now()` on every item that has a purchase and no `cleared_at`, and returns the count.

**Chosen because** a trip is over when it is over; clearing only the current store's bought items would leave the other store's from the same trip lingering. Idempotent by construction: a second call clears nothing and reports zero.

### Undo also un-clears

Undoing a purchase deletes the purchase row and sets `cleared_at` back to NULL.

**Chosen because** a cleared item is not reachable from the client, so this only matters to a direct API caller — but the invariant "no purchase ⇒ not cleared" is cheap to keep and stops a confusing state (cleared but outstanding) from ever existing.

## Risks / Trade-offs

- **Bought items pile up if nobody clears** → Accepted by decision; the clear control shows a count so the pile is visible. A time-based sweep is a small later change if it proves necessary.
- **The API's item list now includes bought items** → Any consumer that assumed "listed means outstanding" would be wrong. There is one consumer, the client, and it is changed here. The representation already carried `purchase`, so the distinction was always visible.
- **Existing bought items become visible on deploy** → Every item bought before this change appears in the bought group after the upgrade, since none is cleared. That is a one-time surprise on the first open, and "clear bought" resolves it in one tap. Worth mentioning in the release notes; not worth a backfill that guesses which old purchases the household still wants to see.

## Migration Plan

1. Archive `add-item-catalogue-and-categories` first, so the view requirements this change modifies are in the main spec.
2. Add `cleared_at`; no backfill.
3. Repository query, service, endpoint.
4. Client: bought group, row-tap undo, clear control; remove the undo banner and its test.
5. On deploy, expect the historical bought items in the bought group; clear them.

**Rollback:** drop the column. Purchases are untouched throughout.

## Open Questions

- Whether a bought item's row should show who bought it and when. The data is there; it is a presentation choice that can be made when the group is first seen in use.
