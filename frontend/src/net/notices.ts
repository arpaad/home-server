/**
 * Notices: what did not go through, and why.
 *
 * When the server refuses a queued change for good — the store was deleted
 * meanwhile, the item no longer exists — the change is dropped and the
 * member is told, once, in a notice they can dismiss. Nothing stays pending
 * forever, and nothing disappears in silence.
 */

import { useSyncExternalStore } from 'react'

export interface Notice {
  id: string
  text: string
}

let notices: Notice[] = []
const listeners = new Set<() => void>()

function emit(): void {
  for (const listener of listeners) listener()
}

export function pushNotice(text: string): void {
  notices = [...notices, { id: crypto.randomUUID(), text }]
  emit()
}

export function dismissNotice(id: string): void {
  notices = notices.filter((n) => n.id !== id)
  emit()
}

export function useNotices(): Notice[] {
  return useSyncExternalStore(
    (callback) => {
      listeners.add(callback)
      return () => listeners.delete(callback)
    },
    () => notices,
  )
}
