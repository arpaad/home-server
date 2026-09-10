/**
 * Which member is using this device.
 *
 * The choice is persisted per device because it is a convenience, not a
 * credential: this release identifies members so purchases can be attributed,
 * and does not authenticate them.
 */

import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'home.memberId'

function read(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY)
  } catch {
    // Private windows and blocked site data both throw; the app still works,
    // the member just has to pick again.
    return null
  }
}

export function useMember(): {
  memberId: string | null
  setMemberId: (id: string | null) => void
} {
  const [memberId, setState] = useState<string | null>(read)

  useEffect(() => {
    try {
      if (memberId) window.localStorage.setItem(STORAGE_KEY, memberId)
      else window.localStorage.removeItem(STORAGE_KEY)
    } catch {
      // Nothing to do: the selection simply will not survive a reload.
    }
  }, [memberId])

  const setMemberId = useCallback((id: string | null) => setState(id), [])

  return { memberId, setMemberId }
}
