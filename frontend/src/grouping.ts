/**
 * Arranging the list by category.
 *
 * Grouping is presentation only: it never decides which items appear, the
 * server already did. The one rule that matters is that an item with no
 * category is still shown — in a final "Uncategorised" group — because a
 * freshly typed item must never quietly vanish into a group nobody looks at.
 */

import type { Category, Item } from './api/types'

export interface Group {
  key: string
  category: Category | null
  items: Item[]
}

export function groupByCategory(items: Item[]): Group[] {
  // The server returns rows already in category order with uncategorised
  // last, so a single pass preserves the household's ordering.
  const groups: Group[] = []
  let current: Group | null = null
  for (const item of items) {
    const key = item.category?.id ?? 'uncategorised'
    if (!current || current.key !== key) {
      current = { key, category: item.category, items: [] }
      groups.push(current)
    }
    current.items.push(item)
  }
  return groups
}
