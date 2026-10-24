## 1. Schema

- [x] 1.1 Add `shopping_items.important`, boolean, not null, `server_default false`, to the ORM and generate the migration; verify autogenerate then reports no difference against the model, and the suite (which builds its schema from the migrations) passes

## 2. Domain, repository, service, API

- [x] 2.1 Carry `important` through the domain item, mapping, repository `add`/`update` and the service; verify tests that an item is not important by default, can be created important, and that an edit sets and clears the flag while leaving other fields alone
- [x] 2.2 Accept `important` on create and edit and return it on every item; verify contract tests that a created-important item lists with `important: true`, and that an edit older than the last applied one does not change the flag
- [x] 2.3 Verify by test that importance does not change membership: an important item assigned only to Lidl is absent from Spar's view

## 3. Client

- [x] 3.1 Rename the filter chip to "Anywhere" and render it after the stores; verify an end-to-end test that it is last and selected by default, and update the existing tests that click it
- [x] 3.2 Add the important toggle to the add and edit form, and the flag to optimistic create and edit; verify the build type-checks
- [x] 3.3 Put outstanding important items in a "!" group above every category group, and the "!" mark on important rows; verify an end-to-end test that an important item is listed first and only once, returns to its category when the flag is cleared, and keeps its mark in the bought group
- [x] 3.4 Add "Add (again)" with the form reset and the status bar; verify end-to-end tests that after it the form is empty and the bar names the item as added, and that offline the bar says pending

## 4. Acceptance

- [x] 4.1 Update `README.md` and `AGENTS.md` for the flag and the renamed chip; verify the documented flow matches the app
- [ ] 4.2 Walk the scenarios on a phone
