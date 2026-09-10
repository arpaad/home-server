/**
 * The HTTP client.
 *
 * Every failure becomes an ApiError carrying the server's own message. The
 * spec requires that a change which could not be saved is never shown as
 * saved, so nothing here swallows an error or substitutes an empty result.
 */

import type { Item, ItemCreate, ItemUpdate, Member, Purchase, Store } from './types'

/** Same origin in production; Vite proxies this to the backend in dev. */
const BASE = '/api'

export class ApiError extends Error {
  readonly status: number
  /** Items blocking a store deletion, when the server named them. */
  readonly items: string[]

  constructor(status: number, message: string, items: string[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.items = items
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
}
