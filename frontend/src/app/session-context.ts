import { createContext, useContext } from 'react'
import type { Account } from '../lib/accounts'

export type SessionState = {
  user: Account | null
  phase: 'loading' | 'ready' | 'offline'
  setUser: (user: Account | null) => void
  restore: () => Promise<void>
}
export const SessionContext = createContext<SessionState | null>(null)
export function useSession() {
  const session = useContext(SessionContext)
  if (!session) throw new Error('Session provider is required')
  return session
}
