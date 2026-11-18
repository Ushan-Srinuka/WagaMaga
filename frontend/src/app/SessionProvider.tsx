import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { ApiError, restoreSession, type Account } from '../lib/accounts'
import { SessionContext, type SessionState } from './session-context'

export default function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Account | null>(null)
  const [phase, setPhase] = useState<SessionState['phase']>('loading')
  const restore = useCallback(async () => {
    try {
      setUser((await restoreSession()).user)
      setPhase('ready')
    } catch (error) {
      setUser(null)
      setPhase(
        error instanceof ApiError && error.status === 401 ? 'ready' : 'offline',
      )
    }
  }, [])
  useEffect(() => {
    let cancelled = false
    void restoreSession().then(
      (result) => {
        if (!cancelled) {
          setUser(result.user)
          setPhase('ready')
        }
      },
      (error) => {
        if (!cancelled) {
          setUser(null)
          setPhase(
            error instanceof ApiError && error.status === 401
              ? 'ready'
              : 'offline',
          )
        }
      },
    )
    const received = (event: Event) => {
      setUser((event as CustomEvent<Account>).detail)
      setPhase('ready')
    }
    const expired = () => {
      setUser(null)
      setPhase('ready')
    }
    const offline = () => {
      setUser(null)
      setPhase('offline')
    }
    window.addEventListener('account-session', received)
    window.addEventListener('account-expired', expired)
    window.addEventListener('account-offline', offline)
    return () => {
      cancelled = true
      window.removeEventListener('account-session', received)
      window.removeEventListener('account-expired', expired)
      window.removeEventListener('account-offline', offline)
    }
  }, [])
  return (
    <SessionContext.Provider value={{ user, setUser, phase, restore }}>
      {children}
    </SessionContext.Provider>
  )
}
