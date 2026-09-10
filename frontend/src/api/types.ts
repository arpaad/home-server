/** Wire types, mirroring the backend's DTOs. */

export type Unit = 'piece' | 'box' | 'kg' | 'g' | 'l' | 'dl' | 'm' | 'cm'

export const UNITS: readonly Unit[] = ['piece', 'box', 'kg', 'g', 'l', 'dl', 'm', 'cm']

export type ItemOrigin = 'manual' | 'recipe'

export interface Member {
  id: string
  name: string
}

export interface Store {
  id: string
  name: string
}

export interface Purchase {
  member_id: string
  bought_at: string
}

export interface Item {
  id: string
  name: string
  quantity: number
  unit: Unit
  /** Empty means the item may be bought anywhere, so it shows under every store. */
  stores: Store[]
  /** ISO date; until it arrives the item stays out of the shopping views. */
  available_from: string | null
  origin: ItemOrigin
  purchase: Purchase | null
}

export interface ItemCreate {
  name: string
  quantity?: number
  unit?: Unit
  store_ids?: string[]
  available_from?: string | null
}

export interface ItemUpdate {
  name?: string
  quantity?: number
  unit?: Unit
  store_ids?: string[]
  available_from?: string | null
  clear_available_from?: boolean
}
