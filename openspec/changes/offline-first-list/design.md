## Context

See `proposal.md` — Why. What shapes the approach:

- The client's server data already lives in a TanStack Query cache (`queries.ts`), with every mutation invalidating the lists on success. The cache is in memory only and starts empty on every open.
- The service worker (`vite.config.ts`) precaches the app shell and nothing else: `runtimeCaching: []`, and `/api` is on the navigate-fallback denylist. That was a deliberate decision in `add-shopping-list` — a worker-served list would look current while being stale.
- The spec's current rule, *Connectivity is required for changes*, was written for that world: no local state, so an unsent change had to be reported as failed. This change replaces the world, so it replaces the rule.
- Item ids are minted by the server on insert. Edits carry no timestamp. Delete of a missing item is a 404.
- The backend commits before the response (fixed in `show-bought-until-cleared`); replays therefore see their own earlier writes.
- HTTPS is required for a service worker off `localhost`. On the laptop this is not a constraint; on the Pi it is, and it is handled by the Pi deployment, not here.

## Goals / Non-Goals

**Goals:**

- The list is usable — read and changed — with no server, and honest about it.
- Replaying a queue produces the same server state as doing the same things online, once.
- Nothing stays pending forever; nothing silently disappears.
- The service worker's rule stays: it never serves data as current.

**Non-Goals:**

- A general offline framework. This is the shopping list's outbox, nothing more.
- CRDTs or merge UI. Later edit wins is a stated, tested policy, not an approximation of something better.
- Offline management of stores, categories, catalogue.

## Decisions

### The query cache is persisted; the service worker still caches nothing from the API

TanStack Query's cache is persisted to IndexedDB (`persistQueryClient` with an async persister), so the last-known stores, categories, catalogue and every fetched list view survive a restart. The worker's `runtimeCaching` stays empty.

**Chosen because** the app needs to *know* whether what it shows is current — `dataUpdatedAt`, `fetchStatus === 'paused'` — in order to say "last confirmed at 18:40" and to mark rows pending. A worker-served cached response is indistinguishable from a live one at the point of use; the requirement forbids exactly that indistinguishability. Persisting the query cache keeps the knowledge in the layer that renders it.

**Alternatives considered.** *Workbox NetworkFirst for `/api`*: least code, and the reason it was ruled out in the first change still holds. *A hand-written IndexedDB mirror of every entity*: full control, and a second data model to keep in sync with the server's; the query cache already is that mirror.

### Mutations are the outbox

TanStack Query mutations run with `networkMode: 'offlineFirst'`; while `onlineManager` reports offline they *pause* rather than fail, and paused mutations are persisted alongside the cache and resumed with `resumePausedMutations()` on start and on reconnect. Resumption is in order.

**Chosen because** it is the mechanism the library provides for precisely this, it keeps every write on the one code path the app already uses, and it survives a restart without a second queue implementation. Each mutation applies an optimistic update to the cache (`onMutate`) so the local copy changes at once; the pending mark is derived from `useMutationState` — a row is pending while a mutation touching its id is pending or paused.

**Alternatives considered.** *A separate outbox table with a custom replayer*: more control over batching and conflict handling, at the cost of a second system doing what mutations already do. *Background Sync API*: replays even with the app closed, Chrome-on-Android only, and it would need the custom outbox anyway; deferred as a progressive enhancement.

### "Reachable" is decided by trying

`onlineManager` is driven by `navigator.onLine` *and* by request outcomes: a network failure marks the app offline; a subsequent success marks it online. A periodic probe of `/health` while the app is open and offline turns it back on without waiting for a browser event.

**Chosen because** `navigator.onLine` is true on any Wi-Fi, including one with no route to the house, and false only when every radio is off. The app on mobile data outside the house is "online" to the browser and offline to us. Trying is the only honest test.

### Every replayed operation is idempotent, by construction

- **Create** carries a client-generated UUID. The server treats a create with an existing id as "return the existing item", so a create that reached the server but whose response was lost lands once on replay. This also lets an offline-created item be edited, bought or removed offline: the id exists before the server has seen it.
- **Edit** carries `edited_at`, the phone's time when the edit was made. The item gains `updated_at`, set to the edit's time on apply. An edit whose `edited_at` is older than `updated_at` is answered 200 with the current item and a flag saying it was not applied — not 409, because the client should drop it quietly, not retry it.
- **Remove** of a missing item is 204. A removal that already happened, or that the other phone did first, is not a failure.
- **Buy** is already idempotent; **undo** and **clear** are naturally so.

**Chosen because** the queue will be replayed after partial failures, and "did that one go through?" must never matter. Idempotency at each operation is cheaper and more reliable than de-duplication in the queue.

`updated_at` is only compared, never displayed; the household time zone plays no part. An edit without `edited_at` (an online client, or any other caller) always applies.

### Later edit wins by edit time, not by arrival

**Chosen because** it is what the household asked for, and arrival order would make an offline phone syncing at 11:00 overwrite an online edit made at 10:05 with one made at 10:00. Field-level merging was considered and rejected: the item is small, edits are rare, and "the later edit of *this item* wins" is what a person expects to have happened.

**Trade-off, stated:** a phone with a clock badly ahead of real time wins every conflict; one badly behind loses them. Phones synchronise their clocks; accepted.

### Permanent refusals are dropped, temporary ones retried

A 4xx other than 408 or 429 is permanent: the mutation is removed, the queries invalidated so the server's truth replaces the optimistic state, and a notice pushed to a small dismissible list ("*ketchup* could not be updated: store Aldi no longer exists") built from the API's error message. 5xx, 408, 429 and network failures keep the mutation paused or retrying.

**Chosen because** a queue that can wedge on one bad entry blocks everything behind it, and the member has no way to see which entry is at fault. Telling them once and moving on is the honest response; the local copy is corrected in the same step so the app does not keep showing a change the server rejected.

### Management pages disable writes offline

The stores, categories and catalogue pages read from the persisted cache but disable their write controls while offline, with a one-line reason.

**Chosen because** their conflicts are real (rename versus delete of a category), their use is at home, and half the value of the offline change is in keeping its surface small.

## Risks / Trade-offs

- **Optimistic state diverges from the server before sync** → Every mutation's `onSettled` invalidates, so the first successful contact replaces the optimistic view with the server's. The pending mark tells the member which rows are not yet confirmed.
- **Persisted cache grows** → Only list views, stores, categories, catalogue: a few hundred small rows. The persister is given a `maxAge` of seven days; a copy older than that is discarded, and the app says it has nothing to show, rather than presenting a week-old list.
- **A replay half-completes** (three of five sent, then signal lost again) → Each is idempotent and they resume in order; the three are done, the two remain pending. That is the intended state.
- **The clock trade-off above** → Documented; not mitigated.
- **A stale pending mark after a crash mid-mutation** → Mutation state is persisted with the cache; on restart, a mutation that was in flight is resumed, not orphaned.
- **Playwright's `setOffline` does not fire `navigator.onLine` reliably in every driver** → The tests assert on behaviour (requests blocked, then allowed) rather than on the flag, and the app's own probe-based detection is what makes that work.

## Migration Plan

1. Backend first: client-supplied id on create, `edited_at`/`updated_at` on edit, tolerant delete. All additive; online clients are unaffected. One migration adding `updated_at`, no backfill.
2. Client: persistence and `onlineManager` wiring, then optimistic updates and pending marks, then the notice list, then the management-page guards.
3. Spec: this change's delta reverses *Connectivity is required for changes*; archive after the two changes it layers on.

**Rollback:** the client change is self-contained; reverting it returns to the network-only client, which still works against the extended backend. The `updated_at` column is harmless to leave.

## Open Questions

- Whether to add the Background Sync API later so a queue drains with the app closed. Progressive enhancement; nothing here precludes it.
- Whether a very old persisted copy (past `maxAge`) should still be shown with a strong warning rather than discarded. Deferred until someone hits it.
