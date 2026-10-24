/**
 * Adding an item, and editing one. Reached deliberately, from the + button.
 *
 * "Add (again)" adds and comes straight back to an empty form, for writing
 * up several things in a row. A thin bar then says what happened to the
 * last one — pending until the server has it, added once it does.
 *
 * Choosing a suggestion prefills the category (shown, not editable here —
 * it belongs to the catalogue entry) and the stores (editable, because
 * "we normally get it at Lidl but we are in Spar now" has to stay possible).
 */

import { useMutationState, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'

import { mutationKeys } from '../api/mutations'
import { useCategories, useCreateItem, useDeleteItem, useItems, useStores, useUpdateItem } from '../api/queries'
import type { CatalogueEntry, Category, Item, ItemCreate, Store, Unit } from '../api/types'
import { UNITS } from '../api/types'
import { Typeahead } from '../components/Typeahead'

export function AddPage() {
  const [params] = useSearchParams()
  const editId = params.get('edit')

  const stores = useStores()
  const queryClient = useQueryClient()
  // Bumped by "Add (again)": a fresh key remounts the form, so every field
  // is back to empty with no per-field reset to forget.
  const [round, setRound] = useState(0)
  const [lastAdded, setLastAdded] = useState<Added | null>(null)

  // Look for the item being edited in any list view already in the cache —
  // the member almost always arrives from one, and offline that copy is
  // all there is. Only fetch the full list when nothing cached has it.
  const cached: Item | undefined = editId
    ? queryClient
        .getQueriesData<Item[]>({ queryKey: ['items'] })
        .flatMap(([, data]) => data ?? [])
        .find((item) => item.id === editId)
    : undefined
  // Adding needs the whole list too, to catch a name already on it — the
  // view the member came from may be one store's, and the milk on the list
  // may be for another.
  const allItems = useItems(null, true, editId === null || cached === undefined)

  const editing: Item | undefined = cached ?? (editId ? allItems.data?.find((item) => item.id === editId) : undefined)

  if (editId && !editing && allItems.isPending && allItems.fetchStatus === 'fetching') {
    return <p className="empty">Loading…</p>
  }

  return (
    <section className="page" data-testid="add-page">
      {editId && !editing && (
        <div className="banner banner--error">That item is not in this phone's copy of the list.</div>
      )}
      {/* Keyed so a different item gets a fresh form, initialised from props. */}
      <ItemEditor
        key={editing?.id ?? `new-${round}`}
        editing={editing}
        stores={stores.data ?? []}
        onAddedAgain={(added) => {
          setLastAdded(added)
          setRound((n) => n + 1)
        }}
      />
      {lastAdded && <AddedBar key={lastAdded.id} added={lastAdded} />}
    </section>
  )
}

interface Added {
  id: string
  name: string
}

const BAR_MS = 3000

/**
 * The thin bar after "Add (again)". Its words come from the add's own state
 * in the mutation queue, never from having pressed the button: offline the
 * add is only queued, and a queued change is never shown as saved.
 */
function AddedBar({ added }: { added: Added }) {
  const states = useMutationState({
    filters: {
      mutationKey: mutationKeys.createItem,
      predicate: (m) => (m.state.variables as ItemCreate | undefined)?.id === added.id,
    },
    select: (m) => ({ status: m.state.status, paused: m.state.isPaused }),
  })
  const state = states.at(-1)
  const phase = state === undefined ? 'pending' : state.status === 'pending' && state.paused ? 'paused' : state.status
  // Shown for a while after each change of phase, then gone by itself.
  const [hiddenPhase, setHiddenPhase] = useState<string | null>(null)
  useEffect(() => {
    const timer = window.setTimeout(() => setHiddenPhase(phase), BAR_MS)
    return () => window.clearTimeout(timer)
  }, [phase])

  // A refusal is reported by the notice it raises; this bar just goes.
  if (phase === 'error' || phase === hiddenPhase) return null

  const text =
    phase === 'success'
      ? `“${added.name}” added`
      : phase === 'paused'
        ? `“${added.name}” pending — will send when back online`
        : `“${added.name}” pending — sending…`

  return (
    <div
      className={`toast ${phase === 'success' ? '' : 'toast--pending'}`}
      role="status"
      data-testid="added-bar"
      data-phase={phase}
    >
      {text}
    </div>
  )
}

function ItemEditor({
  editing,
  stores,
  onAddedAgain,
}: {
  editing: Item | undefined
  stores: Store[]
  onAddedAgain: (added: Added) => void
}) {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const createItem = useCreateItem()
  const updateItem = useUpdateItem()
  const deleteItem = useDeleteItem()
  // The list view this form was opened from, store filter and all.
  const from = (location.state as { from?: string } | null)?.from ?? '/'
  const [duplicate, setDuplicate] = useState<Item | null>(null)

  const [name, setName] = useState(editing?.name ?? '')
  const [quantity, setQuantity] = useState(String(editing?.quantity ?? 1))
  const [unit, setUnit] = useState<Unit>(editing?.unit ?? 'piece')
  const [storeIds, setStoreIds] = useState<string[]>(editing?.stores.map((s) => s.id) ?? [])
  const [availableFrom, setAvailableFrom] = useState(editing?.available_from ?? '')
  const [category, setCategory] = useState<Category | null>(editing?.category ?? null)
  const [important, setImportant] = useState(editing?.important ?? false)
  // Only a deliberate choice is sent. Leaving the picker alone must never
  // uncategorise a known item that was typed without choosing a suggestion.
  const [categoryTouched, setCategoryTouched] = useState(false)
  const categories = useCategories()

  const toggleStore = (storeId: string) =>
    setStoreIds((current) =>
      current.includes(storeId) ? current.filter((id) => id !== storeId) : [...current, storeId],
    )

  const applySuggestion = (entry: CatalogueEntry) => {
    setName(entry.name)
    setCategory(entry.category)
    setCategoryTouched(false)
    setStoreIds(entry.stores.map((s) => s.id))
  }

  const chooseCategory = (categoryId: string) => {
    setCategory((categories.data ?? []).find((c) => c.id === categoryId) ?? null)
    setCategoryTouched(true)
  }

  const back = () => void navigate(from)

  /**
   * An outstanding item with this name on this phone's copy of the list,
   * including ones added here and not yet sent. The server holds the same
   * rule; this only saves the round trip and lets us offer the edit.
   */
  const alreadyListed = (wanted: string): Item | undefined => {
    const key = wanted.trim().toLowerCase()
    return queryClient
      .getQueriesData<Item[]>({ queryKey: ['items'] })
      .flatMap(([, data]) => data ?? [])
      .find((item) => item.purchase === null && item.name.trim().toLowerCase() === key)
  }

  const remove = () => {
    if (!editing) return
    deleteItem.mutate(editing.id)
    back()
  }

  const save = (again: boolean) => {
    const parsed = Number(quantity)
    const payload = {
      name: name.trim(),
      quantity: Number.isFinite(parsed) && parsed > 0 ? parsed : 1,
      unit,
      // Always explicit: the chips are the truth, never the catalogue.
      store_ids: storeIds,
      available_from: availableFrom === '' ? null : availableFrom,
      important,
      // The category goes to the entry, so only a deliberate choice is sent.
      ...(category ? { category_id: category.id } : {}),
      ...(categoryTouched && !category ? { clear_category: true } : {}),
    }
    // Local-first: the change applies to the phone's copy at once and is
    // queued; we return to the list without waiting for the server. A
    // refusal surfaces later as a notice, an outage as a pending mark.
    if (editing) {
      updateItem.mutate({
        itemId: editing.id,
        // Later edit wins, by the time this edit was made.
        payload: { ...payload, clear_available_from: availableFrom === '', edited_at: new Date().toISOString() },
      })
    } else {
      const existing = alreadyListed(payload.name)
      if (existing) {
        setDuplicate(existing)
        return
      }
      // The id is chosen here so an item added offline can be edited or
      // bought before the server has seen it, and replayed without landing
      // twice.
      const id = crypto.randomUUID()
      createItem.mutate({ ...payload, id })
      if (again) {
        onAddedAgain({ id, name: payload.name })
        return
      }
    }
    back()
  }

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    save(false)
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
              // Typing past a chosen suggestion drops its prefilled category:
              // this may be a different thing. A category the member picked
              // themselves stays.
              if (!categoryTouched) setCategory(null)
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
        </div>

        <label className="item-form__category">
          <span className="hint">
            Category
            {name.trim() !== '' && (
              <>
                {' '}
                — applies to every <em>{name.trim()}</em>
              </>
            )}
          </span>
          <select
            data-testid="item-category"
            value={category?.id ?? ''}
            onChange={(event) => chooseCategory(event.target.value)}
            style={category ? ({ '--group-colour': category.colour } as React.CSSProperties) : undefined}
          >
            <option value="">Uncategorised</option>
            {(categories.data ?? []).map((option) => (
              <option key={option.id} value={option.id}>
                {option.icon} {option.name}
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
        </label>

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

        <label className="item-form__important">
          <input
            type="checkbox"
            data-testid="item-important"
            checked={important}
            onChange={(event) => setImportant(event.target.checked)}
          />
          <span>
            <strong>!</strong> Must buy — don't come home without it
          </span>
        </label>

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
        </div>

        {/* Their own row, at the bottom: beside the date they were missed. */}
        <div className="item-form__submit">
          {!editing && (
            <button
              type="button"
              className="button"
              data-testid="item-submit-again"
              disabled={busy || name.trim() === ''}
              onClick={() => save(true)}
            >
              Add (again)
            </button>
          )}
          <button
            type="submit"
            className="button button--primary"
            data-testid="item-submit"
            disabled={busy || name.trim() === ''}
          >
            {busy ? 'Saving…' : editing ? 'Save' : 'Add'}
          </button>
        </div>

        {editing && (
          // Rows are swiped away too; this is the way that needs no gesture.
          <button
            type="button"
            className="button button--quiet item-form__remove"
            data-testid="item-remove"
            onClick={remove}
          >
            Remove from list
          </button>
        )}
      </form>

      {duplicate && (
        <div className="dialog-backdrop" onClick={() => setDuplicate(null)}>
          <div
            className="dialog"
            role="alertdialog"
            aria-labelledby="duplicate-text"
            data-testid="duplicate-dialog"
            onClick={(event) => event.stopPropagation()}
          >
            <p className="dialog__text" id="duplicate-text">
              <strong>“{duplicate.name}”</strong> is already on the list —{' '}
              {duplicate.stores.length === 0 ? 'for any store' : `at ${duplicate.stores.map((s) => s.name).join(', ')}`}.
              Edit that one instead?
            </p>
            <div className="dialog__actions">
              <button type="button" className="button" data-testid="duplicate-cancel" onClick={() => setDuplicate(null)}>
                Cancel
              </button>
              <button
                type="button"
                className="button button--primary"
                data-testid="duplicate-edit"
                autoFocus
                onClick={() => void navigate(`/add?edit=${duplicate.id}`, { state: { from }, replace: true })}
              >
                Edit it
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
