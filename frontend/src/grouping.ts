/**
 * Arranging the list: category groups, then one group for what was bought.
 *
 * Grouping is presentation only: it never decides which items appear, the
 * server already did. Two rules matter. An item with no category is still
 * shown, in an "Uncategorised" group, because a freshly typed item must
 * never quietly vanish. And bought items sit in a final group after every
 * outstanding one — out of the way of the shopping, in the way of the
 * end-of-trip review, which is the right order.
 */

import type { Category, Item } from './api/types'

export interface Group {
  key: string
  category: Category | null
  /** True for the single group of bought, uncleared items. */
  bought: boolean
  items: Item[]
}

export function groupByCategory(items: Item[]): Group[] {
  // The server returns outstanding rows in category order, then bought rows
  // most-recent-first, so a single pass preserves both orderings.
  const groups: Group[] = []
  let current: Group | null = null
  for (const item of items) {
    const bought = item.purchase !== null
    const key = bought ? 'bought' : (item.category?.id ?? 'uncategorised')
    if (!current || current.key !== key) {
      current = { key, category: bought ? null : item.category, bought, items: [] }
      groups.push(current)
    }
    current.items.push(item)
  }
  return groups
}

export function countBought(items: Item[]): number {
  return items.filter((item) => item.purchase !== null).length
}
