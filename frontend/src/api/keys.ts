/** Query keys, shared by the hooks and the mutation defaults. */

export const keys = {
  members: ['members'] as const,
  stores: ['stores'] as const,
  categories: ['categories'] as const,
  catalogue: ['catalogue'] as const,
  items: (storeId: string | null, includeUpcoming: boolean) =>
    ['items', storeId ?? 'all', includeUpcoming] as const,
}
