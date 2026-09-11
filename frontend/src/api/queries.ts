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
import { keys } from './keys'
import { mutationKeys, type BuyVariables, type UpdateVariables } from './mutations'
import type {
  CatalogueEntry,
  CatalogueEntryCreate,
  CatalogueEntryUpdate,
  Category,
  CategoryCreate,
  CategoryUpdate,
  Item,
  ItemCreate,
  ItemEditResult,
  Member,
  Store,
} from './types'

export { keys } from './keys'

export function useMembers(): UseQueryResult<Member[]> {
  return useQuery({ queryKey: keys.members, queryFn: api.listMembers })
}

export function useStores(): UseQueryResult<Store[]> {
  return useQuery({ queryKey: keys.stores, queryFn: api.listStores })
}

export function useItems(
  storeId: string | null,
  includeUpcoming: boolean,
  enabled = true,
): UseQueryResult<Item[]> {
  return useQuery({
    queryKey: keys.items(storeId, includeUpcoming),
    queryFn: () => api.listItems({ storeId, includeUpcoming }),
    enabled,
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

// List mutations are keyed and carry no inline callbacks: their function,
// optimistic update and error handling live in mutations.ts, registered as
// defaults, so a mutation paused offline can be resumed after a restart.

export function useCreateItem(): UseMutationResult<Item, Error, ItemCreate> {
  return useMutation({ mutationKey: mutationKeys.createItem })
}

export function useUpdateItem(): UseMutationResult<ItemEditResult, Error, UpdateVariables> {
  return useMutation({ mutationKey: mutationKeys.updateItem })
}

export function useDeleteItem(): UseMutationResult<void, Error, string> {
  return useMutation({ mutationKey: mutationKeys.deleteItem })
}

export function useBuyItem(): UseMutationResult<unknown, Error, BuyVariables> {
  return useMutation({ mutationKey: mutationKeys.buyItem })
}

export function useUndoPurchase(): UseMutationResult<Item, Error, string> {
  return useMutation({ mutationKey: mutationKeys.undoPurchase })
}

export function useClearBought(): UseMutationResult<{ cleared: number }, Error, void> {
  return useMutation({ mutationKey: mutationKeys.clearBought })
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

export function useCreateEntry(): UseMutationResult<CatalogueEntry, Error, CatalogueEntryCreate> {
  const invalidate = useInvalidateLists()
  return useMutation({ mutationFn: api.createEntry, onSuccess: invalidate })
}

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
