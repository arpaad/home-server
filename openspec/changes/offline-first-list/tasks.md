## 1. Backend: make every list operation safe to replay

- [x] 1.1 Add `shopping_items.updated_at` (nullable timestamp) and its migration with no backfill; verify autogenerate matches and the migration round-trips on a copy of the database with the item tables byte-identical
- [x] 1.2 Accept an optional client-supplied `id` on item create, returning the existing item when it already exists; verify a contract test that the same create sent twice yields exactly one item and both responses succeed, and that a create without an id still mints one
- [x] 1.3 Accept an optional `edited_at` on item update; refuse to apply an edit older than the item's `updated_at`, answering 200 with the current item and `applied: false`; set `updated_at` on every applied edit; verify contract tests for the older-edit-loses scenario, for an edit without `edited_at` always applying, and for the response shape
- [x] 1.4 Make deleting a missing item answer 204; verify a contract test and that the existing delete tests still pass
- [x] 1.5 Verify every existing backend test still passes with no edit to what it asserts

## 2. Client: the local copy

- [x] 2.1 Add the query persister (IndexedDB) with a seven-day `maxAge`, restoring the cache before first render; verify an end-to-end test that after loading the list once, going offline and reloading still shows the list
- [x] 2.2 Drive `onlineManager` from request outcomes and a periodic `/health` probe, not only `navigator.onLine`; verify a test that a failed request marks the app offline and a later successful probe marks it online, without a browser online event
- [x] 2.3 Show "last confirmed at …" whenever the list is served from the copy, and "cannot reach the server, nothing to show yet" on a phone that has never loaded it; verify end-to-end tests for both, including that an empty local copy is never rendered as an empty list

## 3. Client: local-first writes

- [x] 3.1 Generate item ids on the client in the add form and send them; verify an end-to-end test that an item added offline can be edited and bought offline, and that after reconnecting it exists on the server exactly once and is bought
- [x] 3.2 Give every list mutation an optimistic update and `networkMode: 'offlineFirst'`, and persist paused mutations with the cache; verify an end-to-end test that buying offline moves the item to the bought group at once, and that the change is sent after reconnecting
- [x] 3.3 Resume paused mutations on start and on reconnect, in order; verify an end-to-end test that changes made offline, followed by closing and reopening the app online, reach the server in the order they were made
- [x] 3.4 Send `edited_at` with every edit; verify an end-to-end test of the spec's 10:00-versus-10:05 scenario using two browser contexts

## 4. Client: honesty

- [x] 4.1 Mark a row pending while any mutation touching its id is paused or in flight, and clear the mark on confirmation; verify an end-to-end test that an offline edit shows the mark, and reconnecting removes it
- [x] 4.2 On a permanent refusal, drop the mutation, invalidate, and push a dismissible notice built from the API's message; verify an end-to-end test of the deleted-store scenario — the notice names the item and the store, the list shows the server's state, and nothing stays pending
- [x] 4.3 Keep temporary failures (network, 5xx, 408, 429) paused or retrying with no notice; verify a test that a 503 followed by a 200 completes the change silently
- [x] 4.4 Disable the write controls on the stores, categories and catalogue pages while offline, with a one-line reason; verify an end-to-end test that renaming a category offline is refused with that reason and nothing is queued

## 5. Acceptance

- [x] 5.1 Verify the service worker still caches nothing under `/api`: an end-to-end test that, with the worker active and the network blocked, an API request fails rather than being served from the worker
- [x] 5.2 Run the whole end-to-end suite online; verify nothing online changed — every prior test passes as it did
- [x] 5.3 Update `README.md` and `AGENTS.md`: local-first behaviour, the pending mark, later-edit-wins, and the invariant that the worker never serves API data; verify the documented flow matches the app
- [ ] 5.4 Walk it on a phone: load the list at home, switch to flight mode, add / edit / buy / undo, switch flight mode off, and watch the other phone catch up; record anything that did not behave as specified
