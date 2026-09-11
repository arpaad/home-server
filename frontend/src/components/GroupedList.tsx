/** The list, arranged by category. See grouping.ts for the rule. */

import type { Item } from '../api/types'
import { groupByCategory } from '../grouping'
import { ItemRow } from './ItemRow'

export function GroupedList({
  items,
  today,
  busy,
  canBuy,
  onBuy,
  onEdit,
  onDelete,
}: {
  items: Item[]
  today: string
  busy: boolean
  canBuy: boolean
  onBuy: (item: Item) => void
  onEdit: (item: Item) => void
  onDelete: (item: Item) => void
}) {
  return (
    <div className="groups" data-testid="grouped-list">
      {groupByCategory(items).map((group) => (
        <section
          key={group.key}
          className="group"
          data-testid="group"
          data-category={group.category?.name ?? 'Uncategorised'}
          style={
            group.category
              ? ({ '--group-colour': group.category.colour } as React.CSSProperties)
              : undefined
          }
        >
          <h2 className={`group__title ${group.category ? '' : 'group__title--none'}`}>
            <span className="group__icon" aria-hidden="true">
              {group.category?.icon ?? '·'}
            </span>
            <span>{group.category?.name ?? 'Uncategorised'}</span>
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
                onBuy={() => onBuy(item)}
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
