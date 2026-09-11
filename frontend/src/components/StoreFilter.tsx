/**
 * The store filter.
 *
 * "Everywhere" is not a store; it is the absence of a filter, showing every
 * outstanding item. Picking a store shows what to put in the basket there,
 * which includes items assigned to no store at all.
 */

import type { Store } from '../api/types'

export function StoreFilter({
  stores,
  selected,
  onSelect,
}: {
  stores: Store[]
  selected: string | null
  onSelect: (storeId: string | null) => void
}) {
  return (
    <nav className="chips" aria-label="Filter by store" data-testid="store-filter">
      <button
        type="button"
        className={`chip ${selected === null ? 'chip--on' : ''}`}
        aria-pressed={selected === null}
        onClick={() => onSelect(null)}
      >
        Everywhere
      </button>
      {stores.map((store) => (
        <button
          key={store.id}
          type="button"
          data-testid={`store-chip-${store.name}`}
          className={`chip ${selected === store.id ? 'chip--on' : ''}`}
          aria-pressed={selected === store.id}
          onClick={() => onSelect(store.id)}
        >
          {store.name}
        </button>
      ))}
    </nav>
  )
}
