import type { ReactNode } from 'react'

import { MemberContext } from './MemberContext'
import { useMember } from './useMember'

export function MemberProvider({ children }: { children: ReactNode }) {
  const state = useMember()
  return <MemberContext.Provider value={state}>{children}</MemberContext.Provider>
}
