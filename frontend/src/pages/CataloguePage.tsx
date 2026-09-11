/**
 * The catalogue: everything the household has ever put on the list.
 *
 * This is where a name typed in a hurry gets its category, once, so every
 * future add carries it. And where the duplicates that prefix matching
 * deliberately keeps visible get merged away.
 */

import { useState } from 'react'
import { Link } from 'react-router'

import { ApiError } from '../api/client'
import {
  useCatalogue,
  useCategories,
  useDeleteEntry,
  useMergeEntry,
  useRenameEntry,
  useStores,
  useUpdateEntry,
} from '../api/queries'
import type { CatalogueEntry } from '../api/types'
import { StatusBanner } from '../components/StatusBanner'

export function CataloguePage() {
  const catalogue = useCatalogue()
  const categories = useCategories()
  const stores = useStores()
  const [error, setError] = useState<unknown>(null)
  const [filter, setFilter] = useState('')

  const entries = (catalogue.data ?? []).filter((entry) =>
    entry.name.toLowerCase().includes(filter.trim().toLowerCase()),
  )

  return (
    <section className="page" data-testid="catalogue-page">
      <header className="page__header">
        <Link to="/" className="button button--quiet">
          ← Back
        </Link>
        <h1 className="page__title">Catalogue</h1>
      </header>

      <p className="hint">
        Everything ever added to the list. Set a category once and every future add of that thing
        carries it.
      </p>

      <StatusBanner error={error} />
      <StatusBanner error={catalogue.error} onRetry={() => void catalogue.refetch()} />

      <input
        className="catalogue-filter"
        data-testid="catalogue-filter"
        placeholder="Find…"
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
      />

      {catalogue.isSuccess && entries.length === 0 && (
        <p className="empty">Nothing in the catalogue yet — it fills itself as you add items.</p>
      )}

      <ul className="manage-list">
        {entries.map((entry) => (
          <EntryRow
            key={entry.id}
            entry={entry}
            all={catalogue.data ?? []}
            categories={categories.data ?? []}
            stores={stores.data ?? []}
            onError={setError}
          />
        ))}
      </ul>
    </section>
  )
}

function EntryRow({
  entry,
  all,
  categories,
  stores,
  onError,
}: {
  entry: CatalogueEntry
  all: CatalogueEntry[]
  categories: { id: string; name: string; icon: string; colour: string }[]
  stores: { id: string; name: string }[]
  onError: (error: unknown) => void
}) {
  const update = useUpdateEntry()
  const rename = useRenameEntry()
  const merge = useMergeEntry()
  const remove = useDeleteEntry()
  const [renaming, setRenaming] = useState(false)
  const [newName, setNewName] = useState(entry.name)
  const [collision, setCollision] = useState<string | null>(null)

  const run = (promise: Promise<unknown>) => {
    onError(null)
    promise.catch((caught: unknown) => onError(caught))
  }

  const setCategory = (categoryId: string) =>
    run(
      update.mutateAsync({
        entryId: entry.id,
        payload: categoryId === '' ? { clear_category: true } : { category_id: categoryId },
      }),
    )

  const toggleStore = (storeId: string) => {
    const current = entry.stores.map((s) => s.id)
    const next = current.includes(storeId)
      ? current.filter((id) => id !== storeId)
      : [...current, storeId]
    run(update.mutateAsync({ entryId: entry.id, payload: { store_ids: next } }))
  }

  const submitRename = (event: React.FormEvent) => {
    event.preventDefault()
    setCollision(null)
    rename
      .mutateAsync({ entryId: entry.id, name: newName.trim() })
      .then(() => setRenaming(false))
      .catch((caught: unknown) => {
        // A collision is not an error to the member: it is the moment they
        // find out this is a duplicate, and the fix is a merge.
        if (caught instanceof ApiError && caught.status === 409 && caught.existingId) {
          setCollision(caught.existingId)
        } else {
          onError(caught)
        }
      })
  }

  const collidingEntry = collision ? all.find((e) => e.id === collision) : undefined

  const doMerge = (intoId: string) => {
    const target = all.find((e) => e.id === intoId)
    if (!target) return
    if (!window.confirm(`Merge "${entry.name}" into "${target.name}"? Items move across; "${entry.name}" is removed.`)) return
    run(merge.mutateAsync({ entryId: entry.id, intoId }).then(() => setRenaming(false)))
  }

  const doRemove = () => {
    if (!window.confirm(`Remove "${entry.name}" from the catalogue?`)) return
    run(remove.mutateAsync(entry.id))
  }

  return (
    <li className="catalogue-row" data-testid={`entry-row-${entry.name}`}>
      <div className="catalogue-row__head">
        {renaming ? (
          <form className="catalogue-rename" onSubmit={submitRename}>
            <input
              data-testid={`rename-input-${entry.name}`}
              value={newName}
              autoFocus
              onChange={(event) => setNewName(event.target.value)}
            />
            <button type="submit" className="button button--primary" data-testid={`rename-save-${entry.name}`}>
              Save
            </button>
            <button
              type="button"
              className="button button--quiet"
              onClick={() => {
                setRenaming(false)
                setCollision(null)
                setNewName(entry.name)
              }}
            >
              Cancel
            </button>
          </form>
        ) : (
          <>
            <span className="catalogue-row__name">{entry.name}</span>
            <span className="manage-row__actions">
              <button type="button" className="icon-button" onClick={() => setRenaming(true)} data-testid={`rename-${entry.name}`}>
                Rename
              </button>
              <button type="button" className="icon-button icon-button--danger" onClick={doRemove}>
                Remove
              </button>
            </span>
          </>
        )}
      </div>

      {collidingEntry && (
        <div className="banner banner--info" data-testid={`collision-${entry.name}`}>
          <span>
            "{collidingEntry.name}" already exists. Merge this into it instead?
          </span>
          <button
            type="button"
            className="banner__action"
            data-testid={`merge-${entry.name}`}
            onClick={() => doMerge(collidingEntry.id)}
          >
            Merge
          </button>
        </div>
      )}

      <div className="catalogue-row__body">
        <label className="catalogue-row__field">
          <span className="hint">Category</span>
          <select
            data-testid={`category-select-${entry.name}`}
            value={entry.category?.id ?? ''}
            onChange={(event) => setCategory(event.target.value)}
          >
            <option value="">Uncategorised</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.icon} {category.name}
              </option>
            ))}
          </select>
        </label>

        <div className="catalogue-row__field">
          <span className="hint">Usually bought at</span>
          <div className="chips chips--small">
            {stores.map((store) => {
              const on = entry.stores.some((s) => s.id === store.id)
              return (
                <button
                  key={store.id}
                  type="button"
                  className={`chip chip--small ${on ? 'chip--on' : ''}`}
                  aria-pressed={on}
                  data-testid={`entry-store-${entry.name}-${store.name}`}
                  onClick={() => toggleStore(store.id)}
                >
                  {store.name}
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </li>
  )
}
