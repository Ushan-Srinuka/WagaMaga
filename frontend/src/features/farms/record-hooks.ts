import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../../lib/accounts'
import { failureText, farmRead } from '../../lib/farms'

export function useRecord<T>(
  path: string | null,
  reader: typeof farmRead = farmRead,
) {
  const [revision, setRevision] = useState(0)
  const reload = useCallback(() => setRevision((n) => n + 1), [])
  const key = `${path}:${revision}`
  const [result, setResult] = useState<{
    key: string
    data?: T
    error?: unknown
  }>({ key: '' })
  useEffect(() => {
    if (!path) return
    let active = true
    void reader<T>(path).then(
      (data) => {
        if (active) setResult({ key, data })
      },
      (error: unknown) => {
        if (active) setResult({ key, error })
      },
    )
    return () => {
      active = false
    }
  }, [path, key, reader])
  return {
    data: result.key === key ? result.data : undefined,
    error: result.key === key ? result.error : undefined,
    loading:
      Boolean(path) && (result.key !== key || (!result.data && !result.error)),
    reload,
    replace: (data: T) => setResult({ key, data }),
  }
}

export function useSave(formatError: (error: unknown) => string = failureText) {
  const mounted = useRef(true)
  const inFlight = useRef(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [blocked, setBlocked] = useState(false)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  async function run<T>(write: () => Promise<T>, success: (value: T) => void) {
    if (inFlight.current || blocked) return
    inFlight.current = true
    setBusy(true)
    setError('')
    try {
      const result = await write()
      if (mounted.current) success(result)
    } catch (failure) {
      if (mounted.current) {
        setError(formatError(failure))
        setBlocked(
          failure instanceof ApiError &&
            [0, 403, 404, 409, 503].includes(failure.status),
        )
      }
    } finally {
      inFlight.current = false
      if (mounted.current) setBusy(false)
    }
  }
  return {
    busy,
    error,
    blocked,
    run,
    reset: () => {
      setError('')
      setBlocked(false)
    },
  }
}
