/**
 * Adding and editing an item.
 *
 * Stores are picked from the ones that exist, never typed. A free-text store
 * name lets a typo silently hide an item from its store's filter, which is
 * the exact failure this whole capability removes — so adding a store is a
 * separate, deliberate action, not something you can do by mistyping here.
 */

import { useState } from 'react'

import type { Item, Store, Unit } from '../api/types'
import { UNITS } from '../api/types'

export interface ItemDraft {
  name: string
  quantity: number
  unit: Unit
  storeIds: string[]
  availableFrom: string | null
}

export function ItemForm({
  stores,
  initial,
  submitLabel,
  busy,
  onSubmit,
  onCancel,
  onAddStore,
}: {
  stores: Store[]
  initial?: Item
  submitLabel: string
  busy: boolean
  onSubmit: (draft: ItemDraft) => void
  onCancel?: () => void
  onAddStore: () => void
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [quantity, setQuantity] = useState(String(initial?.quantity ?? 1))
  const [unit, setUnit] = useState<Unit>(initial?.unit ?? 'piece')
  const [storeIds, setStoreIds] = useState<string[]>(
    initial?.stores.map((store) => store.id) ?? [],
  )
  const [availableFrom, setAvailableFrom] = useState(initial?.available_from ?? '')

  const toggleStore = (storeId: string) => {
    setStoreIds((current) =>
      current.includes(storeId)
        ? current.filter((id) => id !== storeId)
        : [...current, storeId],
    )
  }

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    const parsed = Number(quantity)
    onSubmit({
      name,
      quantity: Number.isFinite(parsed) && parsed > 0 ? parsed : 1,
      unit,
      storeIds,
      availableFrom: availableFrom === '' ? null : availableFrom,
    })
    if (!initial) {
      setName('')
      setQuantity('1')
      setUnit('piece')
      setStoreIds([])
      setAvailableFrom('')
    }
  }

  return (
    <form className="item-form" onSubmit={submit} data-testid="item-form">
      <div className="item-form__row">
        <input
          data-testid="item-name"
          className="item-form__name"
          placeholder="What do we need?"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
        />
        <input
          data-testid="item-quantity"
          className="item-form__quantity"
          type="number"
          min="0.01"
          step="any"
          value={quantity}
          onChange={(event) => setQuantity(event.target.value)}
          aria-label="Quantity"
        />
        <select
          data-testid="item-unit"
          value={unit}
          onChange={(event) => setUnit(event.target.value as Unit)}
          aria-label="Unit"
        >
          {UNITS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      <fieldset className="item-form__stores">
        <legend>
          Buy at <span className="hint">— none selected means anywhere</span>
        </legend>
        <div className="chips">
          {stores.map((store) => (
            <button
              key={store.id}
              type="button"
              data-testid={`pick-store-${store.name}`}
              className={`chip ${storeIds.includes(store.id) ? 'chip--on' : ''}`}
              aria-pressed={storeIds.includes(store.id)}
              onClick={() => toggleStore(store.id)}
            >
              {store.name}
            </button>
          ))}
          <button type="button" className="chip chip--ghost" onClick={onAddStore}>
            + New store
          </button>
        </div>
      </fieldset>

      <div className="item-form__row">
        <label className="item-form__date">
          <span>Not before</span>
          <input
            data-testid="item-available-from"
            type="date"
            value={availableFrom ?? ''}
            onChange={(event) => setAvailableFrom(event.target.value)}
          />
        </label>
        <div className="item-form__actions">
          {onCancel && (
            <button type="button" className="button button--quiet" onClick={onCancel}>
              Cancel
            </button>
          )}
          <button
            type="submit"
            className="button button--primary"
            data-testid="item-submit"
            disabled={busy || name.trim() === ''}
          >
            {busy ? 'Saving…' : submitLabel}
          </button>
        </div>
      </div>
    </form>
  )
}
