# frontend

The household's progressive web client: React, TypeScript, Vite.

It is a plain SPA on purpose. The API serves the built files from its own
origin, so there is no Node process in the deployment and no CORS to
configure — which is also why this is not Next.js: there is no server slot
for it to fill.

## Working on it

```
npm install
npm run dev          # http://127.0.0.1:5173, proxies /api to the backend
```

The dev server proxies `/api` to `http://127.0.0.1:8080`, so start the
backend first (`make db-up && make run`, or `make up` from the repo root).
Override with `HOME_API_URL`.

## Checks

```
npm run lint         # oxlint
npm run typecheck    # tsc
npm run build        # type-check, bundle, generate the service worker
npm run test:e2e     # Playwright, against a real backend
```

The end-to-end tests run against the production build and a real API with a
real database, because the rule they exist to prove — an item with no store
belongs to every store — lives in SQL. A mocked API would only prove the mock
agrees with itself.

From the repository root: `make client-lint`, `make e2e`, and
`make e2e-deployed` (against the stack on :8080).

## Two things that are requirements, not preferences

- **The service worker precaches the app shell only.** List data always goes
  to the network. A cached list would look current while being wrong, which
  is worse than showing nothing.
- **Stores are picked, never typed.** A free-text store name lets a typo hide
  an item from the store it belongs to — the exact failure this whole feature
  removes. Adding a store is a separate, deliberate action.
