/**
 * Arranging the list: what must be bought, then category groups, then one
 * group for what was bought.
 *
 * Grouping is presentation only: it never decides which items appear, the
 * server already did. Two rules matter. An item with no category is still
 * shown, in an "Uncategorised" group, because a freshly typed item must
 * never quietly vanish. And bought items sit in a final group after every
 * outstanding one — out of the way of the shopping, in the way of the
 * end-of-trip review, which is the right order. Important outstanding items
 * go in a first group, above everything, because forgetting them is the
 * one mistake the trip cannot afford. They leave their category group to do
 * so: an item appears once.
 *
 * Importance is arranged here rather than ordered by the server so that
 * flagging an item offline moves it at once, from the optimistic copy.
 */

import type { Category, Item } from './api/types'

export interface Group {
  key: string
  category: Category | null
  /** True for the single group of bought, uncleared items. */
  bought: boolean
  /** True for the single group of outstanding items that must be bought. */
  important: boolean
  items: Item[]
}

function isMustBuy(item: Item): boolean {
  return item.important && item.purchase === null
}

export function groupByCategory(items: Item[]): Group[] {
  const groups: Group[] = []
  const mustBuy = items.filter(isMustBuy)
  if (mustBuy.length > 0) {
    groups.push({ key: 'important', category: null, bought: false, important: true, items: mustBuy })
  }
  // The server returns outstanding rows in category order, then bought rows
  // most-recent-first, so a single pass preserves both orderings.
  let current: Group | null = null
  for (const item of items) {
    if (isMustBuy(item)) continue
    const bought = item.purchase !== null
    const key = bought ? 'bought' : (item.category?.id ?? 'uncategorised')
    if (!current || current.key !== key) {
      current = { key, category: bought ? null : item.category, bought, important: false, items: [] }
      groups.push(current)
    }
    current.items.push(item)
  }
  return groups
}

export function countBought(items: Item[]): number {
  return items.filter((item) => item.purchase !== null).length
}
