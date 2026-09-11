/**
 * The main screen: for taking things off the list.
 *
 * This is the screen used while walking around a shop, so it holds only what
 * that needs — the list, the store filter, and a way to mark things bought.
 * Adding is one deliberate step away behind the + button, because an entry
 * form sitting under rows that are themselves tap targets is a mis-tap risk
 * exactly when one hand is full.
 */

import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { useBuyItem, useDeleteItem, useItems, useStores, useUndoPurchase } from '../api/queries'
import type { Item } from '../api/types'
import { GroupedList } from '../components/GroupedList'
import { StatusBanner } from '../components/StatusBanner'
import { StoreFilter } from '../components/StoreFilter'
import { useCurrentMember } from '../member/MemberContext'
import { todayIso } from '../today'

export function ListPage() {
  const navigate = useNavigate()
  const { memberId } = useCurrentMember()
  const [storeId, setStoreId] = useState<string | null>(null)
  const [planning, setPlanning] = useState(false)
  const [lastBought, setLastBought] = useState<Item | null>(null)
  const [actionError, setActionError] = useState<unknown>(null)

  // Planning at home shows upcoming items; standing in a shop must not.
  const includeUpcoming = planning && storeId === null

  const stores = useStores()
  const items = useItems(storeId, includeUpcoming)
  const buyItem = useBuyItem(memberId)
  const undoPurchase = useUndoPurchase()
  const deleteItem = useDeleteItem()

  const today = useMemo(() => todayIso(), [])

  const run = (promise: Promise<unknown>) => {
    setActionError(null)
    promise.catch((error: unknown) => setActionError(error))
  }

  const buy = (item: Item) => run(buyItem.mutateAsync(item.id).then(() => setLastBought(item)))
  const undo = () => {
    if (!lastBought) return
    run(undoPurchase.mutateAsync(lastBought.id).then(() => setLastBought(null)))
  }

  return (
    <>
      <StatusBanner error={actionError} />
      <StatusBanner error={items.error ?? stores.error} onRetry={() => void items.refetch()} />

      {memberId === null && (
        <div className="banner banner--info" data-testid="pick-member-hint">
          Choose who you are in the header, so what you buy is recorded against you.
        </div>
      )}

      <StoreFilter stores={stores.data ?? []} selected={storeId} onSelect={setStoreId} />

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
          <GroupedList
            items={items.data}
            today={today}
            busy={buyItem.isPending || deleteItem.isPending}
            canBuy={memberId !== null}
            onBuy={buy}
            onEdit={(item) => void navigate(`/add?edit=${item.id}`)}
            onDelete={(item) => run(deleteItem.mutateAsync(item.id))}
          />
        )}
      </main>

      <Link to="/add" className="fab" data-testid="add-button" aria-label="Add an item">
        +
      </Link>
    </>
  )
}
