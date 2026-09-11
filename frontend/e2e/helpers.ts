import type { APIRequestContext } from '@playwright/test'

/** The API the client talks to, reached directly for test setup and teardown. */
export const API = process.env.E2E_API_URL ?? 'http://127.0.0.1:8080/api'

export interface Store {
  id: string
  name: string
}
export interface Category {
  id: string
  name: string
  icon: string
  colour: string
}
export interface Entry {
  id: string
  name: string
  category: Category | null
  stores: Store[]
}
export interface Item {
  id: string
  name: string
  stores: Store[]
  category: Category | null
}

/** Categories the seed installs; left alone so the dev database stays usable. */
const SEEDED = new Set(['produce', 'bakery', 'dairy', 'meat', 'frozen', 'drinks', 'household', 'other'])

async function json<T>(request: APIRequestContext, path: string): Promise<T> {
  const response = await request.get(`${API}${path}`)
  if (!response.ok()) throw new Error(`GET ${path}: ${response.status()} ${await response.text()}`)
  return response.json() as Promise<T>
}

/**
 * Remove every item, catalogue entry, store, and test-made category, so each
 * test starts from a known state. Order matters: an entry cannot go while an
 * item refers to it, and a store cannot go while an outstanding item does.
 */
export async function resetList(request: APIRequestContext): Promise<void> {
  for (const item of await json<Item[]>(request, '/shopping/items?include_upcoming=true')) {
    await request.delete(`${API}/shopping/items/${item.id}`)
  }
  for (const entry of await json<Entry[]>(request, '/shopping/catalogue')) {
    // Bought items are not listed, so their entries survive (RESTRICT, by
    // design). Strip whatever a test set on them so nothing leaks forward.
    await request.patch(`${API}/shopping/catalogue/${entry.id}`, {
      data: { clear_category: true, store_ids: [] },
    })
    await request.delete(`${API}/shopping/catalogue/${entry.id}`)
  }
  for (const store of await json<Store[]>(request, '/shopping/stores')) {
    await request.delete(`${API}/shopping/stores/${store.id}`)
  }
  for (const category of await json<Category[]>(request, '/shopping/categories')) {
    if (!SEEDED.has(category.name.toLowerCase())) {
      await request.delete(`${API}/shopping/categories/${category.id}`)
    }
  }
}

export async function createStore(request: APIRequestContext, name: string): Promise<Store> {
  const response = await request.post(`${API}/shopping/stores`, { data: { name } })
  if (!response.ok()) throw new Error(`could not create store ${name}: ${await response.text()}`)
  return response.json()
}

export async function createCategory(
  request: APIRequestContext,
  name: string,
  icon = '🧪',
  colour = '#3a8ac4',
): Promise<Category> {
  const response = await request.post(`${API}/shopping/categories`, {
    data: { name, icon, colour },
  })
  if (!response.ok()) throw new Error(`could not create category ${name}: ${await response.text()}`)
  return response.json()
}

export async function seededCategory(request: APIRequestContext, name: string): Promise<Category> {
  const all = await json<Category[]>(request, '/shopping/categories')
  const found = all.find((c) => c.name.toLowerCase() === name.toLowerCase())
  if (!found) throw new Error(`seeded category ${name} is missing — run make seed`)
  return found
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

export async function entryFor(request: APIRequestContext, name: string): Promise<Entry> {
  const entries = await json<Entry[]>(request, '/shopping/catalogue')
  const found = entries.find((e) => e.name.toLowerCase() === name.toLowerCase())
  if (!found) throw new Error(`no catalogue entry named ${name}`)
  return found
}

export async function setEntry(
  request: APIRequestContext,
  name: string,
  payload: { category_id?: string; store_ids?: string[] },
): Promise<Entry> {
  const entry = await entryFor(request, name)
  const response = await request.patch(`${API}/shopping/catalogue/${entry.id}`, { data: payload })
  if (!response.ok()) throw new Error(`could not update entry ${name}: ${await response.text()}`)
  return response.json()
}
