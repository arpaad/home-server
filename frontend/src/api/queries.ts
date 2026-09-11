/**
 * Data access through a query cache with explicit loading and error states.
 *
 * "Connectivity is required" is a requirement about how failures are shown, so
 * every hook here surfaces its error rather than falling back to an empty
 * list — an empty list and a failed request must never look the same.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query'

import { api } from './client'
import type {
  CatalogueEntry,
  CatalogueEntryUpdate,
  Category,
  CategoryCreate,
  CategoryUpdate,
  Item,
  ItemCreate,
  ItemUpdate,
  Member,
  Store,
} from './types'

export const keys = {
  members: ['members'] as const,
  stores: ['stores'] as const,
  categories: ['categories'] as const,
  catalogue: ['catalogue'] as const,
  items: (storeId: string | null, includeUpcoming: boolean) =>
    ['items', storeId ?? 'all', includeUpcoming] as const,
}

export function useMembers(): UseQueryResult<Member[]> {
  return useQuery({ queryKey: keys.members, queryFn: api.listMembers })
}

export function useStores(): UseQueryResult<Store[]> {
  return useQuery({ queryKey: keys.stores, queryFn: api.listStores })
}

export function useItems(
  storeId: string | null,
  includeUpcoming: boolean,
): UseQueryResult<Item[]> {
  return useQuery({
    queryKey: keys.items(storeId, includeUpcoming),
    queryFn: () => api.listItems({ storeId, includeUpcoming }),
  })
}

export function useCategories(): UseQueryResult<Category[]> {
  return useQuery({ queryKey: keys.categories, queryFn: api.listCategories })
}

export function useCatalogue(): UseQueryResult<CatalogueEntry[]> {
  return useQuery({ queryKey: keys.catalogue, queryFn: api.listCatalogue })
}

/**
 * Every mutation invalidates everything derived from the list. Categories
 * decide grouping and the catalogue decides prefills, so a change to either
 * has to reach the list too — and at this data size, refetching a few small
 * lists is cheaper than reasoning about which one changed.
 */
function useInvalidateLists() {
  const client = useQueryClient()
  return () => {
    void client.invalidateQueries({ queryKey: ['items'] })
    void client.invalidateQueries({ queryKey: keys.stores })
    void client.invalidateQueries({ queryKey: keys.categories })
    void client.invalidateQueries({ queryKey: keys.catalogue })
  }
}

export function useCreateItem(): UseMutationResult<Item, Error, ItemCreate> {
  const invalidate = useInvalidateLists()
  return useMutation({ mutationFn: api.createItem, onSuccess: invalidate })
}

export function useUpdateItem(): UseMutationResult<
  Item,
  Error,
  { itemId: string; payload: ItemUpdate }
> {
  const invalidate = useInvalidateLists()
  return useMutation({
    mutationFn: ({ itemId, payload }) => api.updateItem(itemId, payload),
    onSuccess: invalidate,
  })
}

export function useDeleteItem(): UseMutationResult<void, Error, string> {
  const invalidate = useInvalidateLists()
  return useMutation({ mutationFn: api.deleteItem, onSuccess: invalidate })
}

export function useBuyItem(
  memberId: string | null,
): UseMutationResult<unknown, Error, string> {
  const invalidate = useInvalidateLists()
  return useMutation({
    mutationFn: (itemId: string) => api.buyItem(itemId, memberId),
    onSuccess: invalidate,
  })
}

export function useUndoPurchase(): UseMutationResult<Item, Error, string> {
  const invalidate = useInvalidateLists()
  return useMutation({ mutationFn: api.undoPurchase, onSuccess: invalidate })
}

export function useCreateStore(): UseMutationResult<Store, Error, string> {
  const invalidate = useInvalidateLists()
  return useMutation({ mutationFn: api.createStore, onSuccess: invalidate })
}

export function useDeleteStore(): UseMutationResult<void, Error, string> {
  const invalidate = useInvalidateLists()
  return useMutation({ mutationFn: api.deleteStore, onSuccess: invalidate })
}

// ---- categories ----

export function useCreateCategory(): UseMutationResult<Category, Error, CategoryCreate> {
  const invalidate = useInvalidateLists()
  return useMutation({ mutationFn: api.createCategory, onSuccess: invalidate })
}

export function useUpdateCategory(): UseMutationResult<
  Category,
  Error,
  { categoryId: string; payload: CategoryUpdate }
> {
  const invalidate = useInvalidateLists()
  return useMutation({
    mutationFn: ({ categoryId, payload }) => api.updateCategory(categoryId, payload),
    onSuccess: invalidate,
  })
}

export function useReorderCategories(): UseMutationResult<Category[], Error, string[]> {
  const invalidate = useInvalidateLists()
  return useMutation({ mutationFn: api.reorderCategories, onSuccess: invalidate })
}

export function useDeleteCategory(): UseMutationResult<
  { entries_uncategorised: number },
  Error,
  string
> {
  const invalidate = useInvalidateLists()
  return useMutation({ mutationFn: api.deleteCategory, onSuccess: invalidate })
}

// ---- catalogue ----

export function useUpdateEntry(): UseMutationResult<
  CatalogueEntry,
  Error,
  { entryId: string; payload: CatalogueEntryUpdate }
> {
  const invalidate = useInvalidateLists()
  return useMutation({
    mutationFn: ({ entryId, payload }) => api.updateEntry(entryId, payload),
    onSuccess: invalidate,
  })
}

export function useRenameEntry(): UseMutationResult<
  CatalogueEntry,
  Error,
  { entryId: string; name: string }
> {
  const invalidate = useInvalidateLists()
  return useMutation({
    mutationFn: ({ entryId, name }) => api.renameEntry(entryId, name),
    onSuccess: invalidate,
  })
}

export function useMergeEntry(): UseMutationResult<
  CatalogueEntry,
  Error,
  { entryId: string; intoId: string }
> {
  const invalidate = useInvalidateLists()
  return useMutation({
    mutationFn: ({ entryId, intoId }) => api.mergeEntry(entryId, intoId),
    onSuccess: invalidate,
  })
}

export function useDeleteEntry(): UseMutationResult<void, Error, string> {
  const invalidate = useInvalidateLists()
  return useMutation({ mutationFn: api.deleteEntry, onSuccess: invalidate })
}
