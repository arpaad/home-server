/**
 * One item on the list, and what a finger can do to it.
 *
 * Tap the row to edit it; swipe right to mark it bought (or, on a bought
 * row, to undo); swipe left to remove it. The round tick still marks bought
 * and undoes. Text buttons on every row were small, crowded targets and
 * noise on every line; on a phone a tap and a swipe are the natural moves.
 *
 * A swipe only acts past a clear threshold, and the row shows what letting
 * go will do while it moves, so a sloppy thumb springs back rather than
 * removing something.
 */

import { useRef, useState } from 'react'

import type { Item } from '../api/types'

/** Horizontal travel before a move counts as a swipe rather than a tap or a scroll. */
const SLOP_PX = 10
/** How far a swipe must travel to act: at least this, or a share of the row. */
const MIN_COMMIT_PX = 96
const COMMIT_SHARE = 0.3

function formatQuantity(item: Item): string {
  const rounded = Number.isInteger(item.quantity)
    ? String(item.quantity)
    : item.quantity.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
  return `${rounded} ${item.unit}`
}

function formatDate(iso: string): string {
  const date = new Date(`${iso}T00:00:00`)
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

interface Drag {
  pointerId: number
  startX: number
  startY: number
  /** Decided once the move is clearly horizontal; until then it may be a scroll. */
  swiping: boolean
}

export function ItemRow({
  item,
  today,
  busy,
  canBuy,
  pending,
  onBuy,
  onUndo,
  onEdit,
  onDelete,
}: {
  item: Item
  today: string
  busy: boolean
  canBuy: boolean
  pending: boolean
  onBuy: () => void
  onUndo: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const upcoming = item.available_from !== null && item.available_from > today
  const bought = item.purchase !== null
  const canSwipeRight = bought || canBuy

  const [offset, setOffset] = useState(0)
  const drag = useRef<Drag | null>(null)
  // A swipe ends with a click on whatever is under the finger; that click
  // must not also open the editor.
  const swallowClick = useRef(false)

  const threshold = (row: HTMLElement) => Math.max(MIN_COMMIT_PX, row.offsetWidth * COMMIT_SHARE)

  const onPointerDown = (event: React.PointerEvent<HTMLLIElement>) => {
    if (busy || (event.pointerType === 'mouse' && event.button !== 0)) return
    drag.current = { pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, swiping: false }
  }

  const onPointerMove = (event: React.PointerEvent<HTMLLIElement>) => {
    const d = drag.current
    if (!d || d.pointerId !== event.pointerId) return
    const dx = event.clientX - d.startX
    const dy = event.clientY - d.startY
    if (!d.swiping) {
      if (Math.abs(dy) > SLOP_PX && Math.abs(dy) > Math.abs(dx)) {
        drag.current = null // a scroll; leave it to the browser
        return
      }
      if (Math.abs(dx) <= SLOP_PX) return
      d.swiping = true
      event.currentTarget.setPointerCapture(event.pointerId)
    }
    setOffset(dx > 0 && !canSwipeRight ? 0 : dx)
  }

  const finish = (event: React.PointerEvent<HTMLLIElement>) => {
    const d = drag.current
    drag.current = null
    if (!d?.swiping) return
    swallowClick.current = true
    const limit = threshold(event.currentTarget)
    const dx = event.clientX - d.startX
    setOffset(0)
    if (dx >= limit && canSwipeRight) {
      if (bought) onUndo()
      else onBuy()
    } else if (dx <= -limit) {
      onDelete()
    }
  }

  const onCancel = () => {
    drag.current = null
    setOffset(0)
  }

  const onRowClick = () => {
    if (swallowClick.current) {
      swallowClick.current = false
      return
    }
    onEdit()
  }

  const reveal = offset > 0 ? 'right' : offset < 0 ? 'left' : null

  return (
    <li
      className={`swipe ${reveal ? `swipe--${reveal}` : ''}`}
      data-testid="item"
      data-bought={bought ? 'true' : 'false'}
      data-pending={pending ? 'true' : 'false'}
      data-important={item.important ? 'true' : 'false'}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={finish}
      onPointerCancel={onCancel}
    >
      {/* What letting go will do, uncovered as the row slides. */}
      <div className="swipe__under" aria-hidden="true">
        <span className="swipe__label swipe__label--right">{bought ? '↩ Undo' : '✓ Bought'}</span>
        <span className="swipe__label swipe__label--left">Remove 🗑</span>
      </div>

      <div
        className={`item ${upcoming ? 'item--upcoming' : ''} ${bought ? 'item--bought' : ''} ${pending ? 'item--pending' : ''} ${item.important ? 'item--important' : ''} ${offset === 0 ? 'item--settled' : ''}`}
        style={offset === 0 ? undefined : { transform: `translateX(${offset}px)` }}
      >
        {/* The same control marks bought and undoes it: on a bought row the
            tick is filled, and tapping it is the undo. */}
        <button
          type="button"
          className={`item__check ${bought ? 'item__check--done' : ''}`}
          data-testid={bought ? `undo-${item.name}` : `buy-${item.name}`}
          aria-label={bought ? `Undo buying ${item.name}` : `Mark ${item.name} as bought`}
          aria-pressed={bought}
          disabled={busy || (!bought && !canBuy)}
          title={bought ? 'Tap to undo' : canBuy ? 'Mark as bought' : 'Choose who you are first'}
          onClick={bought ? onUndo : onBuy}
        >
          {bought ? '✓' : ''}
        </button>

        {/* The whole body is the tap target for editing. */}
        <button
          type="button"
          className="item__body"
          aria-label={`Edit ${item.name}`}
          data-testid={`edit-${item.name}`}
          onClick={onRowClick}
        >
          <span className="item__line">
            {item.important && (
              <span className="item__important" data-testid="important-mark" title="Must buy">
                !
              </span>
            )}
            <span className="item__name" data-testid="item-name-text">
              {item.name}
            </span>
            {pending && (
              // Saved on this phone, not yet confirmed by the server. Never
              // shown as saved; never hidden either.
              <span className="tag tag--pending" data-testid="pending-mark" title="Not yet sent to the server">
                pending
              </span>
            )}
            <span className="item__quantity">{formatQuantity(item)}</span>
          </span>

          {(item.stores.length > 0 || item.available_from !== null) && (
            <span className="item__meta">
              {/* No store means anywhere; saying so on every such row is noise. */}
              {item.stores.map((store) => (
                <span key={store.id} className="tag">
                  {store.name}
                </span>
              ))}
              {item.available_from !== null && (
                <span className={`tag ${upcoming ? 'tag--later' : ''}`}>
                  {upcoming ? `from ${formatDate(item.available_from)}` : 'available'}
                </span>
              )}
            </span>
          )}
        </button>
      </div>
    </li>
  )
}
