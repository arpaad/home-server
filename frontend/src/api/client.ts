/**
 * The HTTP client.
 *
 * Every failure becomes an ApiError carrying the server's own message. The
 * spec requires that a change which could not be saved is never shown as
 * saved, so nothing here swallows an error or substitutes an empty result.
 */

import type {
  CatalogueEntry,
  CatalogueEntryCreate,
  CatalogueEntryUpdate,
  Category,
  CategoryCreate,
  CategoryUpdate,
  Item,
  ItemCreate,
  ItemUpdate,
  Member,
  Purchase,
  Store,
} from './types'

/** Same origin in production; Vite proxies this to the backend in dev. */
const BASE = '/api'

export class ApiError extends Error {
  readonly status: number
  /** Items blocking a deletion, when the server named them. */
  readonly items: string[]
  /** On a rename collision: the entry already carrying that name. */
  readonly existingId: string | null

  constructor(status: number, message: string, items: string[] = [], existingId: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.items = items
    this.existingId = existingId
  }
}

/** Thrown when the server could not be reached at all. */
export class OfflineError extends ApiError {
  constructor() {
    super(0, 'Could not reach the server. Your change was not saved.')
    this.name = 'OfflineError'
  }
}

interface ErrorBody {
  detail?: string
  items?: string[]
  existing_id?: string | null
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { 'content-type': 'application/json', ...(init.headers ?? {}) },
    })
  } catch {
    throw new OfflineError()
  }

  if (!response.ok) {
    let body: ErrorBody = {}
    try {
      body = (await response.json()) as ErrorBody
    } catch {
      // A non-JSON error body is still an error; fall through to the status.
    }
    throw new ApiError(
      response.status,
      body.detail ?? `Request failed with status ${response.status}`,
      body.items ?? [],
      body.existing_id ?? null,
    )
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

function memberHeader(memberId: string | null): HeadersInit {
  return memberId ? { 'X-Household-Member': memberId } : {}
}

export const api = {
  listMembers: () => request<Member[]>('/household/members'),

  listStores: () => request<Store[]>('/shopping/stores'),

  createStore: (name: string) =>
    request<Store>('/shopping/stores', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),

  deleteStore: (storeId: string) =>
    request<void>(`/shopping/stores/${storeId}`, { method: 'DELETE' }),

  listItems: (options: { storeId?: string | null; includeUpcoming?: boolean } = {}) => {
    const params = new URLSearchParams()
    if (options.storeId) params.set('store_id', options.storeId)
    if (options.includeUpcoming) params.set('include_upcoming', 'true')
    const query = params.toString()
    return request<Item[]>(`/shopping/items${query ? `?${query}` : ''}`)
  },

  createItem: (payload: ItemCreate) =>
    request<Item>('/shopping/items', { method: 'POST', body: JSON.stringify(payload) }),

  updateItem: (itemId: string, payload: ItemUpdate) =>
    request<Item>(`/shopping/items/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  deleteItem: (itemId: string) =>
    request<void>(`/shopping/items/${itemId}`, { method: 'DELETE' }),

  buyItem: (itemId: string, memberId: string | null) =>
    request<Purchase>(`/shopping/items/${itemId}/purchase`, {
      method: 'POST',
      headers: memberHeader(memberId),
    }),

  undoPurchase: (itemId: string) =>
    request<Item>(`/shopping/items/${itemId}/purchase`, { method: 'DELETE' }),

  // ---- categories ----

  listCategories: () => request<Category[]>('/shopping/categories'),

  createCategory: (payload: CategoryCreate) =>
    request<Category>('/shopping/categories', { method: 'POST', body: JSON.stringify(payload) }),

  updateCategory: (categoryId: string, payload: CategoryUpdate) =>
    request<Category>(`/shopping/categories/${categoryId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  reorderCategories: (orderedIds: string[]) =>
    request<Category[]>('/shopping/categories/order', {
      method: 'PUT',
      body: JSON.stringify({ ordered_ids: orderedIds }),
    }),

  previewCategoryRemoval: (categoryId: string) =>
    request<{ entries_uncategorised: number }>(
      `/shopping/categories/${categoryId}/removal-preview`,
    ),

  deleteCategory: (categoryId: string) =>
    request<{ entries_uncategorised: number }>(`/shopping/categories/${categoryId}`, {
      method: 'DELETE',
    }),

  // ---- catalogue ----

  listCatalogue: () => request<CatalogueEntry[]>('/shopping/catalogue'),

  createEntry: (payload: CatalogueEntryCreate) =>
    request<CatalogueEntry>('/shopping/catalogue', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  suggest: (prefix: string, signal?: AbortSignal) =>
    request<CatalogueEntry[]>(
      `/shopping/catalogue/suggest?q=${encodeURIComponent(prefix)}`,
      { signal },
    ),

  updateEntry: (entryId: string, payload: CatalogueEntryUpdate) =>
    request<CatalogueEntry>(`/shopping/catalogue/${entryId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  renameEntry: (entryId: string, name: string) =>
    request<CatalogueEntry>(`/shopping/catalogue/${entryId}/rename`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),

  mergeEntry: (entryId: string, intoId: string) =>
    request<CatalogueEntry>(`/shopping/catalogue/${entryId}/merge`, {
      method: 'POST',
      body: JSON.stringify({ into_id: intoId }),
    }),

  deleteEntry: (entryId: string) =>
    request<void>(`/shopping/catalogue/${entryId}`, { method: 'DELETE' }),
}
