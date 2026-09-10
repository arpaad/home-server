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
  onEdit,
  onDelete,
}: {
  item: Item
  today: string
  busy: boolean
  canBuy: boolean
  onBuy: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const upcoming = item.available_from !== null && item.available_from > today

  return (
    <li className={`item ${upcoming ? 'item--upcoming' : ''}`} data-testid="item">
      <button
        type="button"
        className="item__check"
        data-testid={`buy-${item.name}`}
        aria-label={`Mark ${item.name} as bought`}
        disabled={busy || !canBuy}
        title={canBuy ? 'Mark as bought' : 'Choose who you are first'}
        onClick={onBuy}
      />

      <div className="item__body">
        <div className="item__line">
          <span className="item__name" data-testid="item-name-text">
            {item.name}
          </span>
          <span className="item__quantity">{formatQuantity(item)}</span>
        </div>

        <div className="item__meta">
          {item.stores.length === 0 ? (
            <span className="tag tag--anywhere">anywhere</span>
          ) : (
            item.stores.map((store) => (
              <span key={store.id} className="tag">
                {store.name}
              </span>
            ))
          )}
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
