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
import type { Item, ItemCreate, ItemUpdate, Member, Store } from './types'

export const keys = {
  members: ['members'] as const,
  stores: ['stores'] as const,
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

/** Every mutation invalidates the lists, so both views agree immediately. */
function useInvalidateLists() {
  const client = useQueryClient()
  return () => {
    void client.invalidateQueries({ queryKey: ['items'] })
    void client.invalidateQueries({ queryKey: keys.stores })
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
