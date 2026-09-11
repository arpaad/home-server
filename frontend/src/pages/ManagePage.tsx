/**
 * Stores and categories. For tidying up at home, never needed in a shop.
 */

import { useState } from 'react'
import { Link } from 'react-router'

import { api } from '../api/client'
import {
  useCategories,
  useCreateCategory,
  useCreateStore,
  useDeleteCategory,
  useDeleteStore,
  useReorderCategories,
  useStores,
  useUpdateCategory,
} from '../api/queries'
import type { Category } from '../api/types'
import { StatusBanner } from '../components/StatusBanner'
import { useIsOnline } from '../net/connectivity'

const PRESET_COLOURS = [
  '#4c9a2a',
  '#c48a3a',
  '#e0b53a',
  '#b23a3a',
  '#3a8ac4',
  '#7a4cc4',
  '#5a6b7a',
  '#8a8a8a',
  '#1f6f43',
  '#d9534f',
]

export function ManagePage() {
  const online = useIsOnline()
  const [error, setError] = useState<unknown>(null)
  const run = (promise: Promise<unknown>) => {
    setError(null)
    promise.catch((caught: unknown) => setError(caught))
  }

  return (
    <section className="page" data-testid="manage-page">
      <header className="page__header">
        <Link to="/" className="button button--quiet">
          ← Back
        </Link>
        <h1 className="page__title">Stores and categories</h1>
      </header>

      <StatusBanner error={error} />
      {!online && (
        // Tidying up is done at home, with the server. Nothing here is
        // queued: a rename versus a delete on the other phone is a conflict
        // worth avoiding, not merging.
        <p className="offline-note" data-testid="offline-note">
          Cannot reach the server — stores and categories can be changed once it is back.
        </p>
      )}

      <fieldset className="offline-guard" disabled={!online} data-testid="manage-controls">
        <StoresSection run={run} />
        <CategoriesSection run={run} />
      </fieldset>
    </section>
  )
}

function StoresSection({ run }: { run: (p: Promise<unknown>) => void }) {
  const stores = useStores()
  const createStore = useCreateStore()
  const deleteStore = useDeleteStore()
  const [name, setName] = useState('')

  const add = (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    run(createStore.mutateAsync(trimmed).then(() => setName('')))
  }

  return (
    <div className="manage-section" data-testid="stores-section">
      <h2 className="manage-section__title">Stores</h2>
      <ul className="manage-list">
        {(stores.data ?? []).map((store) => (
          <li key={store.id} className="manage-row" data-testid={`store-row-${store.name}`}>
            <span className="manage-row__name">{store.name}</span>
            <button
              type="button"
              className="icon-button icon-button--danger"
              onClick={() => run(deleteStore.mutateAsync(store.id))}
              aria-label={`Remove ${store.name}`}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
      <form className="manage-add" onSubmit={add}>
        <input
          data-testid="new-store-name"
          placeholder="New store"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <button type="submit" className="button" disabled={createStore.isPending || !name.trim()}>
          Add store
        </button>
      </form>
    </div>
  )
}

function CategoriesSection({ run }: { run: (p: Promise<unknown>) => void }) {
  const categories = useCategories()
  const createCategory = useCreateCategory()
  const updateCategory = useUpdateCategory()
  const reorder = useReorderCategories()
  const deleteCategory = useDeleteCategory()

  const [name, setName] = useState('')
  const [icon, setIcon] = useState('📦')
  const [colour, setColour] = useState(PRESET_COLOURS[0] ?? '#8a8a8a')
  const [editing, setEditing] = useState<Category | null>(null)

  const list = categories.data ?? []

  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction
    if (target < 0 || target >= list.length) return
    const ids = list.map((c) => c.id)
    const [moved] = ids.splice(index, 1)
    if (moved === undefined) return
    ids.splice(target, 0, moved)
    run(reorder.mutateAsync(ids))
  }

  const remove = async (category: Category) => {
    // Tell the member what will happen before it happens.
    const preview = await api.previewCategoryRemoval(category.id)
    const n = preview.entries_uncategorised
    const message =
      n === 0
        ? `Remove "${category.name}"?`
        : `Remove "${category.name}"? ${n} catalogue ${n === 1 ? 'entry' : 'entries'} will become uncategorised. Nothing disappears from the list.`
    if (!window.confirm(message)) return
    await deleteCategory.mutateAsync(category.id)
  }

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    if (editing) {
      run(
        updateCategory
          .mutateAsync({ categoryId: editing.id, payload: { name: trimmed, icon, colour } })
          .then(() => {
            setEditing(null)
            setName('')
          }),
      )
    } else {
      run(createCategory.mutateAsync({ name: trimmed, icon, colour }).then(() => setName('')))
    }
  }

  const startEdit = (category: Category) => {
    setEditing(category)
    setName(category.name)
    setIcon(category.icon)
    setColour(category.colour)
  }

  return (
    <div className="manage-section" data-testid="categories-section">
      <h2 className="manage-section__title">
        Categories <span className="hint">— in the order they appear on the list</span>
      </h2>
      <ul className="manage-list">
        {list.map((category, index) => (
          <li
            key={category.id}
            className="manage-row"
            data-testid={`category-row-${category.name}`}
            style={{ '--group-colour': category.colour } as React.CSSProperties}
          >
            <span className="manage-row__swatch" aria-hidden="true">
              {category.icon}
            </span>
            <span className="manage-row__name">{category.name}</span>
            <span className="manage-row__actions">
              <button
                type="button"
                className="icon-button"
                aria-label={`Move ${category.name} up`}
                data-testid={`move-up-${category.name}`}
                disabled={index === 0 || reorder.isPending}
                onClick={() => move(index, -1)}
              >
                ↑
              </button>
              <button
                type="button"
                className="icon-button"
                aria-label={`Move ${category.name} down`}
                data-testid={`move-down-${category.name}`}
                disabled={index === list.length - 1 || reorder.isPending}
                onClick={() => move(index, 1)}
              >
                ↓
              </button>
              <button type="button" className="icon-button" onClick={() => startEdit(category)}>
                Edit
              </button>
              <button
                type="button"
                className="icon-button icon-button--danger"
                onClick={() => run(remove(category))}
                aria-label={`Remove ${category.name}`}
              >
                Remove
              </button>
            </span>
          </li>
        ))}
      </ul>

      <form className="manage-add manage-add--category" onSubmit={submit}>
        <input
          data-testid="category-icon"
          className="manage-add__icon"
          value={icon}
          maxLength={16}
          aria-label="Icon (emoji)"
          onChange={(event) => setIcon(event.target.value)}
        />
        <input
          data-testid="category-name"
          placeholder={editing ? 'Category name' : 'New category'}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <div className="swatches" role="radiogroup" aria-label="Colour">
          {PRESET_COLOURS.map((preset) => (
            <button
              key={preset}
              type="button"
              role="radio"
              aria-checked={colour === preset}
              className={`swatch ${colour === preset ? 'swatch--on' : ''}`}
              style={{ background: preset }}
              onClick={() => setColour(preset)}
              aria-label={preset}
            />
          ))}
        </div>
        <div className="item-form__actions">
          {editing && (
            <button
              type="button"
              className="button button--quiet"
              onClick={() => {
                setEditing(null)
                setName('')
              }}
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            className="button button--primary"
            data-testid="category-submit"
            disabled={createCategory.isPending || updateCategory.isPending || !name.trim()}
          >
            {editing ? 'Save' : 'Add category'}
          </button>
        </div>
      </form>
    </div>
  )
}
