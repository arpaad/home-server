/**
 * Adding an item, and editing one. Reached deliberately, from the + button.
 *
 * Choosing a suggestion prefills the category (shown, not editable here —
 * it belongs to the catalogue entry) and the stores (editable, because
 * "we normally get it at Lidl but we are in Spar now" has to stay possible).
 */

import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'

import { useCreateItem, useItems, useStores, useUpdateItem } from '../api/queries'
import type { CatalogueEntry, Category, Item, Store, Unit } from '../api/types'
import { UNITS } from '../api/types'
import { StatusBanner } from '../components/StatusBanner'
import { Typeahead } from '../components/Typeahead'

export function AddPage() {
  const [params] = useSearchParams()
  const editId = params.get('edit')

  const stores = useStores()
  // The full list, so an item being edited can be found whatever its store
  // or date. Cached, so this costs nothing when arriving from the list.
  const allItems = useItems(null, true)

  const editing: Item | undefined = editId
    ? allItems.data?.find((item) => item.id === editId)
    : undefined

  if (editId && allItems.isPending) {
    return <p className="empty">Loading…</p>
  }

  return (
    <section className="page" data-testid="add-page">
      {editId && allItems.isSuccess && !editing && (
        <div className="banner banner--error">That item is no longer on the list.</div>
      )}
      {/* Keyed so a different item gets a fresh form, initialised from props. */}
      <ItemEditor key={editing?.id ?? 'new'} editing={editing} stores={stores.data ?? []} />
    </section>
  )
}

function ItemEditor({ editing, stores }: { editing: Item | undefined; stores: Store[] }) {
  const navigate = useNavigate()
  const createItem = useCreateItem()
  const updateItem = useUpdateItem()

  const [name, setName] = useState(editing?.name ?? '')
  const [quantity, setQuantity] = useState(String(editing?.quantity ?? 1))
  const [unit, setUnit] = useState<Unit>(editing?.unit ?? 'piece')
  const [storeIds, setStoreIds] = useState<string[]>(editing?.stores.map((s) => s.id) ?? [])
  const [availableFrom, setAvailableFrom] = useState(editing?.available_from ?? '')
  const [category, setCategory] = useState<Category | null>(editing?.category ?? null)
  const [error, setError] = useState<unknown>(null)

  const toggleStore = (storeId: string) =>
    setStoreIds((current) =>
      current.includes(storeId) ? current.filter((id) => id !== storeId) : [...current, storeId],
    )

  const applySuggestion = (entry: CatalogueEntry) => {
    setName(entry.name)
    setCategory(entry.category)
    setStoreIds(entry.stores.map((s) => s.id))
  }

  const back = () => void navigate('/')

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    const parsed = Number(quantity)
    const payload = {
      name: name.trim(),
      quantity: Number.isFinite(parsed) && parsed > 0 ? parsed : 1,
      unit,
      // Always explicit: the chips are the truth, never the catalogue.
      store_ids: storeIds,
      available_from: availableFrom === '' ? null : availableFrom,
    }
    const request = editing
      ? updateItem.mutateAsync({
          itemId: editing.id,
          payload: { ...payload, clear_available_from: availableFrom === '' },
        })
      : createItem.mutateAsync(payload)
    request.then(back).catch((caught: unknown) => setError(caught))
  }

  const busy = createItem.isPending || updateItem.isPending

  return (
    <>
      <header className="page__header">
        <button type="button" className="button button--quiet" onClick={back} data-testid="cancel">
          ← Back
        </button>
        <h1 className="page__title">{editing ? `Edit ${editing.name}` : 'Add to the list'}</h1>
      </header>

      <StatusBanner error={error} />

      <form className="item-form" onSubmit={submit} data-testid="item-form">
        {editing ? (
          <input
            data-testid="item-name"
            className="item-form__name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
          />
        ) : (
          <Typeahead
            value={name}
            onChange={(next) => {
              setName(next)
              // Typing past a chosen suggestion drops its category: the
              // category belongs to the entry, and this may be a new one.
              setCategory(null)
            }}
            onChoose={applySuggestion}
            inputTestId="item-name"
          />
        )}

        <div className="item-form__row">
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
          {category && (
            <span
              className="tag tag--category"
              data-testid="prefilled-category"
              style={{ '--group-colour': category.colour } as React.CSSProperties}
            >
              {category.icon} {category.name}
            </span>
          )}
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
            {stores.length === 0 && (
              <span className="hint">No stores yet — add them under Manage.</span>
            )}
          </div>
        </fieldset>

        <div className="item-form__row">
          <label className="item-form__date">
            <span>Not before</span>
            <input
              data-testid="item-available-from"
              type="date"
              value={availableFrom}
              onChange={(event) => setAvailableFrom(event.target.value)}
            />
          </label>
          <div className="item-form__actions">
            <button
              type="submit"
              className="button button--primary"
              data-testid="item-submit"
              disabled={busy || name.trim() === ''}
            >
              {busy ? 'Saving…' : editing ? 'Save' : 'Add'}
            </button>
          </div>
        </div>
      </form>
    </>
  )
}
