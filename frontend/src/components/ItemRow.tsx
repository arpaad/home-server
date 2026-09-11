/** One item on the list, with the actions that apply to it. */

import type { Item } from '../api/types'

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

export function ItemRow({
  item,
  today,
  busy,
  canBuy,
  onBuy,
  onUndo,
  onEdit,
  onDelete,
}: {
  item: Item
  today: string
  busy: boolean
  canBuy: boolean
  onBuy: () => void
  onUndo: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const upcoming = item.available_from !== null && item.available_from > today
  const bought = item.purchase !== null

  return (
    <li
      className={`item ${upcoming ? 'item--upcoming' : ''} ${bought ? 'item--bought' : ''}`}
      data-testid="item"
      data-bought={bought ? 'true' : 'false'}
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

      <div className="item__body">
        <div className="item__line">
          <span className="item__name" data-testid="item-name-text">
            {item.name}
          </span>
          <span className="item__quantity">{formatQuantity(item)}</span>
        </div>

        <div className="item__meta">
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
        </div>
      </div>

      <div className="item__actions">
        <button type="button" className="icon-button" onClick={onEdit} aria-label={`Edit ${item.name}`}>
          Edit
        </button>
        <button
          type="button"
          className="icon-button icon-button--danger"
          onClick={onDelete}
          aria-label={`Remove ${item.name}`}
          data-testid={`remove-${item.name}`}
        >
          Remove
        </button>
      </div>
    </li>
  )
}
