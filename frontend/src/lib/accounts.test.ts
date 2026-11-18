import { beforeEach, expect, it, vi } from 'vitest'

const user = {
  id: 'one',
  display_name: 'Farmer',
  email: 'farmer@example.com',
  role: 'farmer',
  disabled_at: null,
  deleted_at: null,
  version: 1,
  created_at: '2026-11-16T00:00:00Z',
}
function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status })
}
beforeEach(() => {
  vi.resetModules()
  vi.clearAllMocks()
})

it('shares a refresh in progress and keeps the access token out of browser storage', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(response({ access_token: 'synthetic-token', user }))
  vi.stubGlobal('fetch', fetch)
  const api = await import('./accounts')
  const first = api.restoreSession()
  const second = api.restoreSession()
  expect(first).toBe(second)
  await Promise.all([first, second])
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(localStorage.length).toBe(0)
  expect(sessionStorage.length).toBe(0)
})

it('does not automatically retry a refresh after an uncertain network response', async () => {
  const fetch = vi.fn().mockRejectedValue(new Error('offline'))
  vi.stubGlobal('fetch', fetch)
  const api = await import('./accounts')
  await expect(api.restoreSession()).rejects.toThrow('Connection interrupted')
  expect(fetch).toHaveBeenCalledTimes(1)
})

it('refreshes once for an expired access token then retries the protected request', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(response({ access_token: 'old-token', user }))
    .mockResolvedValueOnce(response({ message: 'Expired' }, 401))
    .mockResolvedValueOnce(response({ access_token: 'new-token', user }))
    .mockResolvedValueOnce(response(user))
  vi.stubGlobal('fetch', fetch)
  const api = await import('./accounts')
  await api.signIn('farmer@example.com', 'a synthetic password')
  await api.request('/me')
  expect(fetch).toHaveBeenCalledTimes(4)
  expect(new Headers(fetch.mock.calls[3][1].headers).get('Authorization')).toBe(
    'Bearer new-token',
  )
})

it('preserves the in-memory session if logout could not reach the server', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(response({ access_token: 'active-token', user }))
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce(response(user))
  vi.stubGlobal('fetch', fetch)
  const api = await import('./accounts')
  await api.signIn('farmer@example.com', 'a synthetic password')
  await expect(api.signOut()).rejects.toThrow('Connection interrupted')
  await api.request('/me')
  expect(new Headers(fetch.mock.calls[2][1].headers).get('Authorization')).toBe(
    'Bearer active-token',
  )
})
