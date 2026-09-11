/**
 * The outbox: every change to the list, defined once, resumable.
 *
 * Mutations are registered as defaults on the query client rather than
 * declared inline in hooks, because a mutation paused while offline is
 * persisted with the cache and resumed after a restart — and a resumed
 * mutation can only find its function and callbacks here. The hooks in
 * queries.ts refer to these by key and add nothing.
 *
 * Each mutation applies its change to every cached list view at once
 * (`onMutate`), so the phone shows the change immediately; the pending mark
 * a row carries comes from the mutation being in flight or paused, not from
 * anything stored on the item. On success the lists are refetched and the
 * server's truth replaces the optimistic one. On a permanent refusal the
 * change is dropped, the lists refetched, and a notice pushed.
 */

import { useMutationState, type QueryClient } from '@tanstack/react-query'

import { pushNotice } from '../net/notices'
import { api, ApiError, isPermanentFailure } from './client'
import { keys } from './keys'
import type { CatalogueEntry, Item, ItemCreate, ItemUpdate, Store } from './types'

export const mutationKeys = {
  createItem: ['createItem'] as const,
  updateItem: ['updateItem'] as const,
  deleteItem: ['deleteItem'] as const,
  buyItem: ['buyItem'] as const,
  undoPurchase: ['undoPurchase'] as const,
  clearBought: ['clearBought'] as const,
}

export interface UpdateVariables {
  itemId: string
  payload: ItemUpdate
}
export interface BuyVariables {
  itemId: string
  memberId: string | null
}

// ---- cache surgery ----

type ItemsKey = readonly ['items', string, boolean]

function viewOf(key: readonly unknown[]): { storeId: string | null; includeUpcoming: boolean } {
  const [, store, upcoming] = key as ItemsKey
  return { storeId: store === 'all' ? null : store, includeUpcoming: upcoming === true }
}

function todayIso(): string {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10)
}

/** The store-and-availability rule, mirrored for the optimistic copy only. */
function belongsInView(item: Item, storeId: string | null, includeUpcoming: boolean): boolean {
  if (item.purchase !== null) {
    // Bought items follow their stores but ignore availability.
    return storeId === null || item.stores.length === 0 || item.stores.some((s) => s.id === storeId)
  }
  if (!includeUpcoming && item.available_from !== null && item.available_from > todayIso()) {
    return false
  }
  if (storeId === null) return true
  return item.stores.length === 0 || item.stores.some((s) => s.id === storeId)
}

/** Outstanding first in their existing order, then bought most-recent-first. */
function arrange(items: Item[]): Item[] {
  const outstanding = items.filter((i) => i.purchase === null)
  const bought = items
    .filter((i) => i.purchase !== null)
    .sort((a, b) => (b.purchase?.bought_at ?? '').localeCompare(a.purchase?.bought_at ?? ''))
  return [...outstanding, ...bought]
}

function patchLists(
  client: QueryClient,
  patch: (items: Item[], view: { storeId: string | null; includeUpcoming: boolean }) => Item[],
): void {
  for (const [key, data] of client.getQueriesData<Item[]>({ queryKey: ['items'] })) {
    if (!data) continue
    client.setQueryData<Item[]>(key, arrange(patch(data, viewOf(key))))
  }
}

function buildOptimisticItem(client: QueryClient, payload: ItemCreate): Item {
  const stores = client.getQueryData<Store[]>(keys.stores) ?? []
  const catalogue = client.getQueryData<CatalogueEntry[]>(keys.catalogue) ?? []
  const entry = catalogue.find((e) => e.name.toLowerCase() === payload.name.trim().toLowerCase())
  return {
    id: payload.id ?? crypto.randomUUID(),
    name: payload.name.trim(),
    quantity: payload.quantity ?? 1,
    unit: payload.unit ?? 'piece',
    stores: stores.filter((s) => payload.store_ids.includes(s.id)),
    available_from: payload.available_from ?? null,
    origin: 'manual',
    purchase: null,
    catalogue_entry_id: entry?.id ?? null,
    category: entry?.category ?? null,
    cleared_at: null,
    updated_at: null,
  }
}

function describe(client: QueryClient, itemId: string): string {
  for (const [, data] of client.getQueriesData<Item[]>({ queryKey: ['items'] })) {
    const found = data?.find((i) => i.id === itemId)
    if (found) return `"${found.name}"`
  }
  return 'an item'
}

function refused(client: QueryClient, what: string, error: unknown): void {
  const reason = error instanceof ApiError ? error.message : 'the server refused it'
  pushNotice(`${what} was not applied: ${reason}`)
  void refreshLists(client)
}

/**
 * Retry forever on anything temporary; give up at once on a refusal.
 *
 * The first delay is short on purpose: after a failed attempt the mutation
 * waits this long before checking whether we are offline and pausing, and
 * only a paused mutation is persisted. A long first delay is a window in
 * which closing the app loses the change.
 */
const retryPolicy = {
  retry: (_count: number, error: unknown) => !isPermanentFailure(error),
  retryDelay: (attempt: number) => (attempt === 0 ? 250 : Math.min(1000 * 2 ** attempt, 30_000)),
  // One scope for every list mutation: mutations sharing a scope run in
  // series, in the order they were made. Without it, resuming a queue runs
  // them all at once, and "buy the item I just added" reaches the server
  // before the add does.
  scope: { id: 'shopping-list' },
}

// ---- registration ----

/**
 * Refetch the lists — after first cancelling any fetch already in flight.
 *
 * Without the cancel there is a race: "submit, then straight back to the
 * list" mounts the list while the write is still landing, so the list's
 * first GET can be in flight when the write completes. Invalidation then
 * dedupes onto that in-flight fetch (it only cancels one that already has
 * data), the stale response arrives last, and the list sits on the old
 * value until something else refetches it.
 */
async function refreshLists(client: QueryClient): Promise<void> {
  await client.cancelQueries({ queryKey: ['items'] })
  await Promise.all([
    client.invalidateQueries({ queryKey: ['items'] }),
    client.invalidateQueries({ queryKey: keys.catalogue }),
  ])
}

export function registerMutationDefaults(client: QueryClient): void {
  const invalidateLists = () => {
    void refreshLists(client)
  }

  client.setMutationDefaults(mutationKeys.createItem, {
    ...retryPolicy,
    mutationFn: (payload: ItemCreate) => api.createItem(payload),
    onMutate: (payload: ItemCreate) => {
      const item = buildOptimisticItem(client, payload)
      patchLists(client, (items, view) =>
        belongsInView(item, view.storeId, view.includeUpcoming) && !items.some((i) => i.id === item.id)
          ? [...items, item]
          : items,
      )
    },
    onError: (error, payload) => {
      if (isPermanentFailure(error)) refused(client, `Adding "${payload.name}"`, error)
    },
    onSuccess: invalidateLists,
  })

  client.setMutationDefaults(mutationKeys.updateItem, {
    ...retryPolicy,
    mutationFn: ({ itemId, payload }: UpdateVariables) => api.updateItem(itemId, payload),
    onMutate: ({ itemId, payload }: UpdateVariables) => {
      const stores = client.getQueryData<Store[]>(keys.stores) ?? []
      patchLists(client, (items) =>
        items.map((i) =>
          i.id !== itemId
            ? i
            : {
                ...i,
                ...(payload.name !== undefined ? { name: payload.name } : {}),
                ...(payload.quantity !== undefined ? { quantity: payload.quantity } : {}),
                ...(payload.unit !== undefined ? { unit: payload.unit } : {}),
                ...(payload.store_ids !== undefined
                  ? { stores: stores.filter((s) => payload.store_ids?.includes(s.id)) }
                  : {}),
                ...(payload.clear_available_from
                  ? { available_from: null }
                  : payload.available_from !== undefined
                    ? { available_from: payload.available_from }
                    : {}),
              },
        ),
      )
    },
    onError: (error, { itemId }) => {
      if (isPermanentFailure(error)) refused(client, `Editing ${describe(client, itemId)}`, error)
    },
    onSuccess: invalidateLists,
  })

  client.setMutationDefaults(mutationKeys.deleteItem, {
    ...retryPolicy,
    mutationFn: (itemId: string) => api.deleteItem(itemId),
    onMutate: (itemId: string) => {
      patchLists(client, (items) => items.filter((i) => i.id !== itemId))
    },
    onError: (error, itemId) => {
      if (isPermanentFailure(error)) refused(client, `Removing ${describe(client, itemId)}`, error)
    },
    onSuccess: invalidateLists,
  })

  client.setMutationDefaults(mutationKeys.buyItem, {
    ...retryPolicy,
    mutationFn: ({ itemId, memberId }: BuyVariables) => api.buyItem(itemId, memberId),
    onMutate: ({ itemId, memberId }: BuyVariables) => {
      const purchase = { member_id: memberId ?? '', bought_at: new Date().toISOString() }
      patchLists(client, (items) => items.map((i) => (i.id === itemId ? { ...i, purchase } : i)))
    },
    onError: (error, { itemId }) => {
      if (isPermanentFailure(error)) refused(client, `Buying ${describe(client, itemId)}`, error)
    },
    onSuccess: invalidateLists,
  })

  client.setMutationDefaults(mutationKeys.undoPurchase, {
    ...retryPolicy,
    mutationFn: (itemId: string) => api.undoPurchase(itemId),
    onMutate: (itemId: string) => {
      patchLists(client, (items) => items.map((i) => (i.id === itemId ? { ...i, purchase: null } : i)))
    },
    onError: (error, itemId) => {
      if (isPermanentFailure(error)) refused(client, `Undoing ${describe(client, itemId)}`, error)
    },
    onSuccess: invalidateLists,
  })

  client.setMutationDefaults(mutationKeys.clearBought, {
    ...retryPolicy,
    mutationFn: () => api.clearBought(),
    onMutate: () => {
      patchLists(client, (items) => items.filter((i) => i.purchase === null))
    },
    onError: (error) => {
      if (isPermanentFailure(error)) refused(client, 'Clearing bought items', error)
    },
    onSuccess: invalidateLists,
  })
}

// ---- pending marks ----

/** Ids of items with a change queued or in flight. */
export function usePendingItemIds(): Set<string> {
  const pending = useMutationState({
    filters: { status: 'pending' },
    select: (m) => ({ key: m.options.mutationKey?.[0], variables: m.state.variables }),
  })
  const ids = new Set<string>()
  for (const { key, variables } of pending) {
    if (key === 'createItem') ids.add((variables as ItemCreate).id ?? '')
    else if (key === 'updateItem' || key === 'buyItem') ids.add((variables as { itemId: string }).itemId)
    else if (key === 'deleteItem' || key === 'undoPurchase') ids.add(variables as string)
  }
  return ids
}

export function usePendingClear(): boolean {
  return (
    useMutationState({
      filters: { status: 'pending', mutationKey: mutationKeys.clearBought },
      select: (m) => m.state.status,
    }).length > 0
  )
}
