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

export interface Category {
  id: string
  name: string
  /** An emoji. */
  icon: string
  /** #rrggbb */
  colour: string
  /** Sort key for the household-wide order. */
  position: number
}

export interface CategoryCreate {
  name: string
  icon: string
  colour: string
}

export interface CategoryUpdate {
  name?: string
  icon?: string
  colour?: string
}

export interface CatalogueEntry {
  id: string
  name: string
  /** null means uncategorised. */
  category: Category | null
  /** Where this is usually bought; offered as a prefill, never a rule. */
  stores: Store[]
  last_used_at: string | null
}

export interface CatalogueEntryUpdate {
  category_id?: string
  clear_category?: boolean
  store_ids?: string[]
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
  catalogue_entry_id: string | null
  /** Derived from the catalogue entry; null means uncategorised. */
  category: Category | null
}

export interface ItemCreate {
  name: string
  quantity?: number
  unit?: Unit
  /**
   * Explicit, even when empty. Omitting it would make the server apply the
   * catalogue's prefill, and the form always knows what its chips show.
   */
  store_ids: string[]
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
