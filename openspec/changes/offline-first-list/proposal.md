## Why

The list is used in shops, and shops are where the signal goes. An Aldi basement, a Lidl at the back of a retail park: exactly when a member is holding the phone with one hand and a basket with the other, the app cannot reach the server. Today that means a blank list, or a change reported as "could not be saved" — honest, but useless in the aisle.

The server also lives at home, on the household's own network, reached by nothing else. Away from home there is no server to reach at all, by design. So "the server is unreachable" is not an error case for this app; it is half of its life. The app has to be built for it.

## What Changes

- **The list works without the server.** Reads come from a local copy that is kept fresh whenever the server is reachable and used as-is when it is not. The app says, visibly, when the copy was last confirmed against the server.

- **Changes to the list are made locally first**, applied to the copy at once, and queued to be sent. A queued change is shown as pending — not as saved — until the server has confirmed it. This is the honest version of the current "never show an unsaved change as saved" rule: the change *is* saved, on this phone, and the app says exactly that.

- **The queue drains whenever the server becomes reachable** — walking back into the house, or the signal returning in the shop — in the order the changes were made. It survives the app being closed.

- **Later edit wins.** If both phones changed the same field while apart, the change made later in time stands. Buying is already idempotent; removing is final. Nothing asks the member to choose.

- **A change the server refuses for good is dropped, and the member is told.** A store deleted by the other phone, an item that no longer exists: the queued change is discarded, the local copy refreshed from the server, and a dismissible notice says what did not go through and why. Nothing stays stuck.

- **Offline is for the list only.** Adding, editing, removing, buying, undoing and clearing work offline. Stores, categories and the catalogue can be *read* offline (so suggestions and store chips still work) but changing them needs the server — that is tidying-up work done at home.

- **Backend support for replay**: item creation accepts a client-generated identifier so an item added offline can be referred to offline and replayed without duplicating; edits carry the time they were made so the server can apply "later edit wins"; and removing something already gone is a success, not an error.

- **BREAKING (spec)**: the requirement *Connectivity is required for changes* is reversed. Its two scenarios keep their names and now describe pending changes and a last-confirmed timestamp.

### Out of Scope

- **Offline editing of stores, categories and the catalogue.** Deliberately; see above.
- **Real-time sync between two phones on the same network.** Refetch on focus remains sufficient at this scale.
- **Conflict prompts.** Later edit wins, silently. A shopping list does not warrant a merge dialogue.
- **Remote access from outside the home network.** Separate plan; this change makes the app *useful* away from home without it.

## Capabilities

### New Capabilities

- `offline-sync`: How the client keeps a local copy of the list, applies changes to it first, queues them, drains the queue, shows what is pending and what was last confirmed, and handles a change the server refuses.

### Modified Capabilities

- `shopping-list`: **Connectivity is required for changes** is reversed to describe local-first behaviour. **Adding an item** accepts a client-supplied identifier. **Editing an item** carries an edit time and applies later-edit-wins. **Removing an item** already gone succeeds.

> **Layering.** `add-item-catalogue-and-categories` and `show-bought-until-cleared` are unarchived and also modify `shopping-list`. This change's MODIFIED blocks are written against the text as those two leave it, and it must be archived after them. It does not touch the requirements they modify except *Adding an item*, *Editing an item* and *Removing an item*, whose text it takes from the catalogue change's delta.

## Impact

**Affected code**

- `frontend/src/api/client.ts`, `queries.ts` — the query cache is persisted to IndexedDB; mutations pause while offline and resume in order; each mutation is idempotent on replay.
- `frontend/src/main.tsx` — persistence and online-state wiring.
- `frontend/src/components/` — the pending badge on a row, the last-confirmed banner, the sync-failure notice.
- `frontend/src/pages/AddPage.tsx` — generates the item id client-side.
- `frontend/vite.config.ts` — the service worker stays shell-only; no API caching in the worker, because the app must know whether data is current and a worker-served response cannot say.
- `backend/app/modules/shopping/dto/item_dto.py`, `service/shopping_list_service.py`, `api/routes.py` — optional `id` on create (idempotent), `edited_at` on update, tolerant delete.
- `backend/app/modules/shopping/repository/orm.py` — `shopping_items.updated_at`. One migration, no backfill needed (null means "never edited", which loses to any edit).
- `frontend/e2e/` — Playwright's `context.setOffline()` is how every scenario here is proven.

**Dependencies**

- Frontend: `@tanstack/query-persist-client-core` + `@tanstack/query-sync-storage-persister` or the async IndexedDB persister, and `idb-keyval`. All small, all from the same project already in use.
- Backend: none.

**Assumptions recorded**

- "Reachable" is decided by trying, not by inspecting the network. The app does not know or care whether it is on the home Wi-Fi.
- Phone clocks are close enough to real time for later-edit-wins to mean what it says. A phone with a badly wrong clock can lose edits; accepted.
- The two phones are the only writers.
