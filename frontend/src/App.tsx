import { useMemo, useState } from 'react'

import { ApiError } from './api/client'
import {
  useBuyItem,
  useCreateItem,
  useCreateStore,
  useDeleteItem,
  useItems,
  useMembers,
  useStores,
  useUndoPurchase,
  useUpdateItem,
} from './api/queries'
import type { Item } from './api/types'
import { ItemForm, type ItemDraft } from './components/ItemForm'
import { ItemRow } from './components/ItemRow'
import { MemberPicker } from './components/MemberPicker'
import { StatusBanner } from './components/StatusBanner'
import { StoreFilter } from './components/StoreFilter'
import { useMember } from './member/useMember'

/** Today in the browser's zone, for deciding what to show as "upcoming". */
function todayIso(): string {
  const now = new Date()
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 10)
}

export default function App() {
  const { memberId, setMemberId } = useMember()
  const [storeId, setStoreId] = useState<string | null>(null)
  const [planning, setPlanning] = useState(false)
  const [editing, setEditing] = useState<Item | null>(null)
  const [lastBought, setLastBought] = useState<Item | null>(null)
  const [actionError, setActionError] = useState<unknown>(null)

  // Planning at home shows upcoming items; standing in a shop must not.
  const includeUpcoming = planning && storeId === null

  const members = useMembers()
  const stores = useStores()
  const items = useItems(storeId, includeUpcoming)

  const createItem = useCreateItem()
  const updateItem = useUpdateItem()
  const deleteItem = useDeleteItem()
  const buyItem = useBuyItem(memberId)
  const undoPurchase = useUndoPurchase()
  const createStore = useCreateStore()

  const today = useMemo(() => todayIso(), [])
  const storeList = stores.data ?? []
  const memberList = members.data ?? []

  const run = (promise: Promise<unknown>) => {
    setActionError(null)
    promise.catch((error: unknown) => setActionError(error))
  }

  const addStore = () => {
    const name = window.prompt('New store name')?.trim()
    if (!name) return
    run(createStore.mutateAsync(name))
  }

  const submitDraft = (draft: ItemDraft) => {
    const payload = {
      name: draft.name.trim(),
      quantity: draft.quantity,
      unit: draft.unit,
      store_ids: draft.storeIds,
      available_from: draft.availableFrom,
    }
    if (editing) {
      run(
        updateItem
          .mutateAsync({
            itemId: editing.id,
            payload: {
              ...payload,
              clear_available_from: draft.availableFrom === null,
            },
          })
          .then(() => setEditing(null)),
      )
    } else {
      run(createItem.mutateAsync(payload))
    }
  }

  const buy = (item: Item) => {
    run(buyItem.mutateAsync(item.id).then(() => setLastBought(item)))
  }

  const undo = () => {
    if (!lastBought) return
    run(undoPurchase.mutateAsync(lastBought.id).then(() => setLastBought(null)))
  }

  const listError = items.error ?? stores.error ?? members.error
  const busy =
    createItem.isPending || updateItem.isPending || deleteItem.isPending || buyItem.isPending

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__title">
          <h1>H.O.M.E.</h1>
          <p className="app__subtitle">The household list</p>
        </div>
        <MemberPicker members={memberList} memberId={memberId} onChange={setMemberId} />
      </header>

      <StatusBanner error={actionError} />
      <StatusBanner error={listError} onRetry={() => void items.refetch()} />

      {memberId === null && memberList.length > 0 && (
        <div className="banner banner--info" data-testid="pick-member-hint">
          Choose who you are, so what you buy is recorded against you.
        </div>
      )}

      <StoreFilter stores={storeList} selected={storeId} onSelect={setStoreId} />

      {storeId === null && (
        <label className="toggle">
          <input
            type="checkbox"
            data-testid="planning-toggle"
            checked={planning}
            onChange={(event) => setPlanning(event.target.checked)}
          />
          <span>Show items that are not due yet</span>
        </label>
      )}

      {lastBought && (
        <div className="banner banner--undo" data-testid="undo-banner">
          <span>Bought {lastBought.name}.</span>
          <button type="button" className="banner__action" onClick={undo}>
            Undo
          </button>
        </div>
      )}

      <main className="app__list">
        {items.isPending ? (
          <p className="empty" data-testid="loading">
            Loading the list…
          </p>
        ) : items.isError ? (
          // Deliberately not an empty list: a failure must never look like
          // "there is nothing to buy".
          <p className="empty empty--error">The list could not be loaded.</p>
        ) : items.data.length === 0 ? (
          <p className="empty" data-testid="empty">
            {storeId === null ? 'Nothing on the list.' : 'Nothing to buy here.'}
          </p>
        ) : (
          <ul className="items">
            {items.data.map((item) => (
              <ItemRow
                key={item.id}
                item={item}
                today={today}
                busy={busy}
                canBuy={memberId !== null}
                onBuy={() => buy(item)}
                onEdit={() => setEditing(item)}
                onDelete={() => run(deleteItem.mutateAsync(item.id))}
              />
            ))}
          </ul>
        )}
      </main>

      <section className="app__compose">
        {editing ? (
          <>
            <h2 className="compose__title">Edit {editing.name}</h2>
            <ItemForm
              key={editing.id}
              stores={storeList}
              initial={editing}
              submitLabel="Save"
              busy={updateItem.isPending}
              onSubmit={submitDraft}
              onCancel={() => setEditing(null)}
              onAddStore={addStore}
            />
          </>
        ) : (
          <ItemForm
            stores={storeList}
            submitLabel="Add"
            busy={createItem.isPending}
            onSubmit={submitDraft}
            onAddStore={addStore}
          />
        )}
      </section>

      <footer className="app__footer">
        {stores.isError && stores.error instanceof ApiError
          ? 'Stores unavailable.'
          : 'On the household network only — no login, so keep it off the internet.'}
      </footer>
    </div>
  )
}
