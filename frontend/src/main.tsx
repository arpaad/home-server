import { QueryClient } from '@tanstack/react-query'
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { del, get, set } from 'idb-keyval'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'

import { registerMutationDefaults } from './api/mutations'
import App from './App'
import './index.css'
import { MemberProvider } from './member/MemberProvider'
import { installConnectivity } from './net/connectivity'

const SEVEN_DAYS = 7 * 24 * 60 * 60 * 1000

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // The list is shared between two people, so a stale view is worth
      // refreshing whenever the app is looked at again.
      refetchOnWindowFocus: true,
      staleTime: 10_000,
      retry: 1,
      // Offline, a query keeps its data and pauses instead of failing —
      // this is what lets the local copy be shown at all.
      networkMode: 'offlineFirst',
      // Must outlive the persister's maxAge, or the cache is dropped before
      // it can be restored.
      gcTime: SEVEN_DAYS,
    },
    mutations: {
      // 'online', not 'offlineFirst': a mutation made while we already know
      // we are offline pauses at once — and only a paused mutation is
      // persisted. An attempt that would fail anyway buys nothing and opens
      // a window in which closing the app loses the change.
      networkMode: 'online',
      gcTime: SEVEN_DAYS,
    },
  },
})

// Every list mutation is defined once here, so one paused while offline can
// be resumed after a restart.
registerMutationDefaults(queryClient)
installConnectivity()

// The local copy: the whole cache — and any paused mutations — kept in
// IndexedDB. A copy older than a week is discarded rather than shown.
const persister = createAsyncStoragePersister({
  storage: {
    getItem: (key) => get<string>(key).then((v) => v ?? null),
    setItem: (key, value) => set(key, value),
    removeItem: (key) => del(key),
  },
  key: 'home.query-cache',
  // Flush quickly: a member who ticks something and pockets the phone must
  // not lose the change to a write that had not happened yet.
  throttleTime: 200,
})

const root = document.getElementById('root')
if (!root) throw new Error('missing #root')

createRoot(root).render(
  <StrictMode>
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{ persister, maxAge: SEVEN_DAYS }}
      onSuccess={() => {
        // Once the copy is restored, send anything that was waiting, then
        // refresh: the first successful contact replaces the optimistic
        // view with the server's.
        void queryClient.resumePausedMutations().then(() => queryClient.invalidateQueries())
      }}
    >
      <BrowserRouter>
        <MemberProvider>
          <App />
        </MemberProvider>
      </BrowserRouter>
    </PersistQueryClientProvider>
  </StrictMode>,
)
