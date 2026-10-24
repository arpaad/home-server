## Why

More friction from using the list in shops.

- **Adding loses your place.** Standing in Lidl, tap +, add something, and the list comes back on Anywhere. The store has to be picked again every time.
- **Rows are crowded and fiddly.** Every row carries "Edit" and "Remove" text buttons — small targets next to each other, and noise on every line. On a phone, the natural moves are a tap and a swipe.
- **The same thing gets written twice.** Someone adds milk for Lidl; the other adds milk for Spar. Both get bought. That double-buying is what this project exists to stop, and the list currently lets it through whenever the name is typed again.
- Two layout irritations: the "household network only" footer shows on every page, including the add form, where it is in the way; and the add buttons share a line with "Not before", which makes them easy to miss.

## What Changes

- **The list remembers the store view.** The selected store is part of the list's address (`/?store=…`). Going to add or edit an item and coming back — by Add, Save, Back or the phone's back gesture — returns to the same store view.
- **Rows respond to gestures instead of text buttons.**
  - tap the row → edit it
  - swipe right → mark it bought (on a bought row: undo)
  - swipe left → remove it
  - the round tick stays, and still marks bought / undoes.
  While swiping, the row reveals what letting go will do. Only a swipe past a clear threshold acts; a shorter one springs back.
  The Edit and Remove buttons go. So that removing does not depend on a gesture alone, the edit form gains a **Remove from list** button.
- **An item already on the list is not added again.** Adding a name (case-insensitive) that an outstanding item already has is refused — by the server, so both phones are held to it, and up front by the add form, which shows a small dialog: *"milk" is already on the list — at Lidl.* with **Edit it** and **Cancel**. A bought item does not count: needing more of something just bought is normal.
- **The footer shows on the list only.**
- **Add and Add (again) sit on their own row** at the bottom of the form.

### Out of Scope

- **Undo for a swiped removal.** A removal is the existing, unrecoverable delete. The threshold and the reveal are the guard. If accidental removals happen in practice, an undo bar is the follow-up.
- **Renaming onto an existing name** while editing. Only adding is guarded.
- **Fuzzy duplicates.** "mlik" is not "milk"; invariant 9 already says why. The catalogue merge is the tool for that.
- Remembering the "not due yet" toggle.

## Capabilities

### Modified Capabilities

- `shopping-list`: new requirements **Returning to the same store view**, **Row gestures** and **An item already on the list is not added twice**.

> **Layering note.** Only adds requirements; can be archived in any order relative to the open changes.

## Impact

**Affected code**

- `backend/.../errors.py` — `DuplicateItemError`, naming the existing item.
- `backend/.../repository/item_repository.py`, `interfaces.py` — `find_outstanding_by_name`.
- `backend/.../service/shopping_list_service.py` — refuse the duplicate in `add_item`, after the replay check.
- `backend/app/core/error_handlers.py` — 409 carrying `existing_id`.
- `frontend/src/pages/ListPage.tsx` — store in the URL; footer moved here from `App.tsx`.
- `frontend/src/components/ItemRow.tsx`, `GroupedList.tsx`, `index.css` — swipe and tap.
- `frontend/src/pages/AddPage.tsx` — return to where you came from, duplicate dialog, Remove button, button row.

**Data**

- No schema change.

**Behaviour change for an offline replay**

- Two phones adding the same name while apart: the second add to reach the server is refused (409), dropped and reported by the existing notice. That is the intended outcome — one milk, not two.
