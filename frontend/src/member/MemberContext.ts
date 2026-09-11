/**
 * Which member is using this device, shared across every screen.
 *
 * One provider at the root, so the header's picker and the list's "can buy"
 * decision are the same state — two separate hooks would each hold their
 * own copy and disagree.
 */

import { createContext, useContext } from 'react'

export interface MemberState {
  memberId: string | null
  setMemberId: (id: string | null) => void
}

export const MemberContext = createContext<MemberState | null>(null)

export function useCurrentMember(): MemberState {
  const state = useContext(MemberContext)
  if (!state) throw new Error('useCurrentMember must be used inside MemberProvider')
  return state
}
