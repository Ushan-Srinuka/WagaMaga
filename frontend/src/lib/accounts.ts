export type Role = 'farmer' | 'advisor' | 'administrator'
export type Account = {
  id: string
  display_name: string
  email: string
  role: Role
  disabled_at: string | null
  deleted_at: string | null
  version: number
  created_at: string
}
export type TokenResult = {
  access_token: string
  user: Account
  expires_in: number
}
export type AccountPage = {
  items: Account[]
  total: number
  page: number
  page_size: number
}

export class ApiError extends Error {
  status: number
  code: string
  constructor(status: number, message: string, code = 'REQUEST_FAILED') {
    super(message)
    this.status = status
    this.code = code
  }
}

let token: string | null = null
let rotation: Promise<TokenResult> | null = null

export function forgetSession() {
  token = null
}

function remember(result: TokenResult) {
  token = result.access_token
  window.dispatchEvent(
    new CustomEvent('account-session', { detail: result.user }),
  )
  return result
}

async function send<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('X-WagaMaga-Client', 'web')
  if (init.body && !headers.has('Content-Type'))
    headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, {
      ...init,
      headers,
      credentials: 'same-origin',
      signal: AbortSignal.timeout(10000),
    })
  } catch {
    throw new ApiError(
      0,
      'Connection interrupted. Check your connection and try again.',
    )
  }
  const body =
    response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    const text =
      response.status === 422
        ? 'Check the form fields and their length requirements.'
        : typeof body?.message === 'string'
          ? body.message
          : 'The request could not be completed.'
    throw new ApiError(response.status, text, body?.code)
  }
  return body as T
}

export function restoreSession(): Promise<TokenResult> {
  if (!rotation) {
    const rotate = () =>
      send<TokenResult>('/auth/refresh', { method: 'POST' }).then(remember)
    // Serialize cookie rotation between tabs. In one tab, share the same promise even in StrictMode.
    rotation = (
      'locks' in navigator
        ? navigator.locks.request('wagamaga-refresh', rotate)
        : rotate()
    )
      .catch((error: unknown) => {
        forgetSession()
        if (error instanceof ApiError && error.status === 401) {
          window.dispatchEvent(new Event('account-expired'))
        } else {
          window.dispatchEvent(new Event('account-offline'))
        }
        throw error
      })
      .finally(() => {
        rotation = null
      })
  }
  return rotation
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
  options: { retryUnauthorized?: boolean } = {},
): Promise<T> {
  try {
    return await send<T>(path, init)
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401 || !token)
      throw error
    if (options.retryUnauthorized === false) throw error
    await restoreSession()
    return send<T>(path, init)
  }
}

export async function signIn(email: string, password: string) {
  return remember(
    await send<TokenResult>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  )
}

export async function signOut() {
  if (rotation) await rotation.catch(() => undefined)
  const logout = () => send('/auth/logout', { method: 'POST' })
  if ('locks' in navigator)
    await navigator.locks.request('wagamaga-refresh', logout)
  else await logout()
  forgetSession()
  window.dispatchEvent(new Event('account-expired'))
}

export function registerAccount(
  display_name: string,
  email: string,
  password: string,
) {
  return send<{ message: string }>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ display_name, email, password }),
  })
}
