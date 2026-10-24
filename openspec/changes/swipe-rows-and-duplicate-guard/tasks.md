## 1. Duplicate guard (server)

- [x] 1.1 Add `find_outstanding_by_name` to the item repository and its Protocol, and refuse a duplicate in `add_item` with `DuplicateItemError`, answered 409 with `existing_id`; verify tests that a case-different name for another store is refused naming the existing item, a bought item does not block, a replayed create with a known id still returns 201, and no catalogue entry is touched by a refused add

## 2. Client

- [x] 2.1 Keep the selected store in the list's URL and return the add form to where it came from; verify an end-to-end test that adding from Lidl, and backing out of an edit from Spar, each return to that store view
- [x] 2.2 Replace the Edit/Remove buttons with tap-to-edit and swipe right/left, with a threshold and a reveal, and add Remove to the edit form; verify end-to-end tests that a long right swipe buys, a long left swipe removes without a purchase, a short swipe changes nothing, a tap opens the editor, and Remove on the edit form removes
- [x] 2.3 Check for an outstanding item of the same name before adding, and show the dialog with Edit it / Cancel; verify end-to-end tests that the dialog names the existing item's store and Edit it opens that item, and that a bought item does not trigger it
- [x] 2.4 Show the footer on the list only, and put Add / Add (again) on their own row; verify by screenshot of the add form

## 3. Acceptance

- [x] 3.1 Update `README.md` and `AGENTS.md`; verify the documented gestures and the duplicate rule match the app
- [ ] 3.2 Walk the scenarios on a phone, in particular that swiping does not fight vertical scrolling
