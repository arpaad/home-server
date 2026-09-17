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

import {
  useBuyItem,
  useCatalogue,
  useCategories,
  useClearBought,
  useDeleteItem,
  useItems,
  useStores,
  useUndoPurchase,
} from '../api/queries'
import type { Item } from '../api/types'
import { GroupedList } from '../components/GroupedList'
import { StatusBanner } from '../components/StatusBanner'
import { StoreFilter } from '../components/StoreFilter'
import { usePendingClear, usePendingItemIds } from '../api/mutations'
import { countBought } from '../grouping'
import { useIsOnline } from '../net/connectivity'
import { useCurrentMember } from '../member/MemberContext'
import { todayIso } from '../today'

function formatConfirmed(at: number): string {
  const date = new Date(at)
  const today = new Date()
  const sameDay = date.toDateString() === today.toDateString()
  return sameDay
    ? date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
    : date.toLocaleString(undefined, { weekday: 'short', hour: '2-digit', minute: '2-digit' })
}

export function ListPage() {
  const navigate = useNavigate()
  const { memberId } = useCurrentMember()
  const [storeId, setStoreId] = useState<string | null>(null)
  const [planning, setPlanning] = useState(false)
  const [actionError, setActionError] = useState<unknown>(null)

  // Planning at home shows upcoming items; standing in a shop must not.
  const includeUpcoming = planning && storeId === null

  const stores = useStores()
  const items = useItems(storeId, includeUpcoming)
  // Kept warm here so the add page has suggestions, store chips and
  // categories from the phone's copy when the server cannot be reached.
  useCatalogue()
  useCategories()
  const buyItem = useBuyItem()
  const undoPurchase = useUndoPurchase()
  const deleteItem = useDeleteItem()
  const clearBought = useClearBought()

  const today = useMemo(() => todayIso(), [])
  const online = useIsOnline()
  const pendingIds = usePendingItemIds()
  const clearPending = usePendingClear()

  const run = (promise: Promise<unknown>) => {
    setActionError(null)
    promise.catch((error: unknown) => setActionError(error))
  }

  const buy = (item: Item) => run(buyItem.mutateAsync({ itemId: item.id, memberId }))
  // The bought row is the undo: no banner that goes away on its own.
  const undo = (item: Item) => run(undoPurchase.mutateAsync(item.id))

  const boughtCount = countBought(items.data ?? [])
  const clear = () => {
    if (boughtCount === 0) return
    run(clearBought.mutateAsync())
  }

  return (
    <>
      <StatusBanner error={actionError} />
      {online && (
        <StatusBanner error={items.error ?? stores.error} onRetry={() => void items.refetch()} />
      )}

      {/* Offline with a copy: say when it was last confirmed. The copy is
          shown, but never as current. */}
      {!online && items.data !== undefined && (
        <div className="banner banner--offline" data-testid="offline-banner">
          Cannot reach the server. Showing the list as last confirmed at{' '}
          <time dateTime={new Date(items.dataUpdatedAt).toISOString()} data-testid="last-confirmed">
            {formatConfirmed(items.dataUpdatedAt)}
          </time>
          {pendingIds.size + (clearPending ? 1 : 0) > 0 &&
            ` · ${pendingIds.size + (clearPending ? 1 : 0)} change${pendingIds.size + (clearPending ? 1 : 0) === 1 ? '' : 's'} waiting to send`}
          .
        </div>
      )}

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

      <main className="app__list">
        {items.isPending && !online ? (
          // Never used on this phone, and no server: there is nothing to
          // show. Not an empty list — an absent one.
          <p className="empty empty--error" data-testid="nothing-yet">
            Cannot reach the server, and this phone has no copy of the list yet.
          </p>
        ) : items.isPending ? (
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
            busy={buyItem.isPending || undoPurchase.isPending || deleteItem.isPending}
            canBuy={memberId !== null}
            pendingIds={pendingIds}
            onBuy={buy}
            onUndo={undo}
            onEdit={(item) => void navigate(`/add?edit=${item.id}`)}
            onDelete={(item) => run(deleteItem.mutateAsync(item.id))}
          />
        )}

        {/* Below everything, and quiet: clearing is the last thing done on a
            trip, and a prominent control at the top was getting tapped by
            accident on the way to something else. */}
        {boughtCount > 0 && (
          <div className="clear-bought" data-testid="clear-bought-banner">
            <button
              type="button"
              className="button button--quiet clear-bought__button"
              data-testid="clear-bought"
              disabled={clearBought.isPending}
              onClick={clear}
            >
              Clear {boughtCount} bought {boughtCount === 1 ? 'item' : 'items'}
            </button>
          </div>
        )}
      </main>

      <Link to="/add" className="fab" data-testid="add-button" aria-label="Add an item">
        +
      </Link>
    </>
  )
}
