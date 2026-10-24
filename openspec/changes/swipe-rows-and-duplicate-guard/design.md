## Decisions

### The store view lives in the URL, and the add page knows where it came from

`/?store=<id>`. Picking a store replaces the history entry (no back-button trail of chips). Links to the add page pass the list's address in router state, and Back / Add / Save return there; the phone's back gesture already does, because the address is in history.

*Rejected:* `localStorage`. It would also survive closing the app, so tomorrow's list at home would open on Lidl and show "Nothing to buy here" — the list looking empty when it isn't.

A store id that no longer exists falls back to Anywhere once the stores are loaded.

### Gestures are pointer events on the row, with `touch-action: pan-y`

The browser keeps vertical scrolling; horizontal movement reaches the row. A move becomes a swipe once it is 10px horizontal and more horizontal than vertical; until then it may still be a tap or a scroll. Letting go past `max(96px, 30% of the row)` acts; anything less springs back. A tap that did not move opens the editor. The tick is its own button and does not open the editor.

Swipe right on an outstanding row needs a chosen member, like the tick; without one the row springs back.

*Rejected:* a gesture library. One component, three outcomes; a dependency is more to keep than the code.

### The duplicate rule is in the service; the dialog is a courtesy

The rule — no two outstanding items with the same trimmed, case-insensitive name — is checked in `ShoppingListService.add_item`, after the client-id replay check (a replayed create still returns its item) and before touching the catalogue. The refusal is a 409 carrying `existing_id`, like the rename collision.

The add form checks its own copy first — every cached list view, plus the full list it now keeps loaded — so the usual case is a dialog, not a round trip. That copy includes items added on this phone but not yet sent, so "Add (again)" twice with the same name is caught too. What the copy cannot see (the other phone's offline add) the server catches on replay, and the existing refusal notice reports.

Matching is by item name rather than catalogue entry, because it is the name a member sees and would call "the same", and it is compared in SQL with `lower(btrim(name))`.

### Remove moves to the edit form as well

Swipe-only would make removal undiscoverable and unreachable without a touch screen. The edit form is one tap away, and removing from there is deliberate.
