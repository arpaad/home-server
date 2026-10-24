/** The list, arranged by category. See grouping.ts for the rule. */

import type { Item } from '../api/types'
import { groupByCategory, type Group } from '../grouping'
import { ItemRow } from './ItemRow'

function title(group: Group): string {
  if (group.important) return 'Must buy'
  if (group.bought) return 'Bought'
  return group.category?.name ?? 'Uncategorised'
}

export function GroupedList({
  items,
  today,
  busy,
  canBuy,
  pendingIds,
  onBuy,
  onUndo,
  onEdit,
  onDelete,
}: {
  items: Item[]
  today: string
  busy: boolean
  canBuy: boolean
  pendingIds: Set<string>
  onBuy: (item: Item) => void
  onUndo: (item: Item) => void
  onEdit: (item: Item) => void
  onDelete: (item: Item) => void
}) {
  return (
    <div className="groups" data-testid="grouped-list">
      {groupByCategory(items).map((group) => (
        <section
          key={group.key}
          className={`group ${group.bought ? 'group--bought' : ''} ${group.important ? 'group--important' : ''}`}
          data-testid="group"
          data-category={title(group)}
          style={
            group.category
              ? ({ '--group-colour': group.category.colour } as React.CSSProperties)
              : undefined
          }
        >
          <h2 className={`group__title ${group.category ? '' : 'group__title--none'}`}>
            <span className="group__icon" aria-hidden="true">
              {group.important ? '!' : group.bought ? '✓' : (group.category?.icon ?? '·')}
            </span>
            <span>{title(group)}</span>
            <span className="group__count">{group.items.length}</span>
          </h2>
          <ul className="items">
            {group.items.map((item) => (
              <ItemRow
                key={item.id}
                item={item}
                today={today}
                busy={busy}
                canBuy={canBuy}
                pending={pendingIds.has(item.id)}
                onBuy={() => onBuy(item)}
                onUndo={() => onUndo(item)}
                onEdit={() => onEdit(item)}
                onDelete={() => onDelete(item)}
              />
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}
