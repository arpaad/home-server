import type { APIRequestContext } from '@playwright/test'

/** The API the client talks to, reached directly for test setup and teardown. */
export const API = process.env.E2E_API_URL ?? 'http://127.0.0.1:8080/api'

export interface Store {
  id: string
  name: string
}
export interface Item {
  id: string
  name: string
  stores: Store[]
}

/**
 * Remove every item and store, so each test starts from a known list.
 *
 * Items go first: a store cannot be deleted while an outstanding item still
 * references it, which is the behaviour under test elsewhere.
 */
export async function resetList(request: APIRequestContext): Promise<void> {
  const items: Item[] = await (
    await request.get(`${API}/shopping/items?include_upcoming=true`)
  ).json()
  for (const item of items) {
    await request.delete(`${API}/shopping/items/${item.id}`)
  }

  const stores: Store[] = await (await request.get(`${API}/shopping/stores`)).json()
  for (const store of stores) {
    await request.delete(`${API}/shopping/stores/${store.id}`)
  }
}

export async function createStore(
  request: APIRequestContext,
  name: string,
): Promise<Store> {
  const response = await request.post(`${API}/shopping/stores`, { data: { name } })
  if (!response.ok()) throw new Error(`could not create store ${name}: ${await response.text()}`)
  return response.json()
}

export async function createItem(
  request: APIRequestContext,
  name: string,
  storeIds: string[] = [],
  availableFrom: string | null = null,
): Promise<Item> {
  const response = await request.post(`${API}/shopping/items`, {
    data: { name, store_ids: storeIds, available_from: availableFrom },
  })
  if (!response.ok()) throw new Error(`could not create item ${name}: ${await response.text()}`)
  return response.json()
}
