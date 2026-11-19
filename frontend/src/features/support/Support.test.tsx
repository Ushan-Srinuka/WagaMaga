import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../../App'
import { SessionContext } from '../../app/session-context'
import { ApiError, request, type Account } from '../../lib/accounts'
import type { MessagePage, Ticket } from '../../lib/support'
import HelpPage from './HelpPage'
import { NewSupportPage, SupportDetailPage } from './SupportPages'

const user: Account = {
  id: 'synthetic-owner',
  email: 'owner@example.com',
  display_name: 'Synthetic farmer',
  role: 'farmer',
  disabled_at: null,
  deleted_at: null,
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
}
const ticket: Ticket = {
  id: 'ticket-one',
  farmer_id: user.id,
  category: 'farm_records',
  subject: 'Synthetic support question',
  status: 'open',
  version: 1,
  created_at: user.created_at,
  updated_at: user.created_at,
  requester_name: user.display_name,
  requester_available: true,
}
const messages: MessagePage = {
  items: [
    {
      id: 'message',
      author_role: 'farmer',
      body: '<b>Synthetic field question</b>',
      ticket_version: 1,
      created_at: user.created_at,
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
}

vi.mock('../../lib/accounts', async (original) => ({
  ...(await original<typeof import('../../lib/accounts')>()),
  request: vi.fn(),
  restoreSession: vi.fn().mockImplementation(async () => ({
    user,
    access_token: 'synthetic',
    expires_in: 900,
  })),
}))
function reads(path: string): unknown {
  if (path === '/help/contact') return { email: null }
  if (path.startsWith('/notifications'))
    return { unread_count: 0, items: [], total: 0, page: 1, page_size: 20 }
  if (path.startsWith('/support/tickets/ticket-one/messages')) return messages
  if (path === '/support/tickets/ticket-one') return ticket
  throw new Error(`Unexpected synthetic support read: ${path}`)
}
let handle: (path: string, init?: RequestInit) => unknown = reads
beforeEach(() => {
  vi.clearAllMocks()
  handle = reads
  vi.mocked(request).mockImplementation(
    async <T,>(path: string, init?: RequestInit) =>
      (await handle(path, init)) as T,
  )
})
function wrap(
  element: React.ReactNode,
  initial = '/',
  signedIn: Account | null = user,
) {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <SessionContext.Provider
        value={{
          user: signedIn,
          phase: 'ready',
          setUser: vi.fn(),
          restore: vi.fn(),
        }}
      >
        {element}
      </SessionContext.Provider>
    </MemoryRouter>,
  )
}
function detail() {
  return wrap(
    <Routes>
      <Route path="/support/:ticketId" element={<SupportDetailPage />} />
    </Routes>,
    '/support/ticket-one',
  )
}
function fill() {
  fireEvent.change(screen.getByLabelText('What do you need help with?'), {
    target: { value: 'farm_records' },
  })
  fireEvent.change(screen.getByLabelText('Subject'), {
    target: { value: 'Synthetic request subject' },
  })
  fireEvent.change(screen.getByLabelText('Your message'), {
    target: { value: 'Synthetic submitted text' },
  })
}

it('creates only submitted support fields and navigates after success', async () => {
  handle = () => ticket
  wrap(
    <Routes>
      <Route path="/support/new" element={<NewSupportPage />} />
      <Route path="/support/ticket-one" element={<p>Saved request opened</p>} />
    </Routes>,
    '/support/new',
  )
  fill()
  fireEvent.click(screen.getByRole('button', { name: 'Send request' }))
  expect(await screen.findByText('Saved request opened')).toBeVisible()
  expect(request).toHaveBeenCalledTimes(1)
  const [path, init, options] = vi.mocked(request).mock.calls[0]
  expect(path).toBe('/support/tickets')
  expect(JSON.parse(String(init?.body))).toEqual({
    category: 'farm_records',
    subject: 'Synthetic request subject',
    body: 'Synthetic submitted text',
  })
  expect(options).toEqual({ retryUnauthorized: false })
})

it('keeps an uncertain submission and blocks duplicate sending pending review', async () => {
  handle = () => {
    throw new ApiError(0, 'Interrupted')
  }
  wrap(<NewSupportPage />)
  fill()
  fireEvent.click(screen.getByRole('button', { name: 'Send request' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'may already be saved',
  )
  expect(screen.getByLabelText('Your message')).toHaveValue(
    'Synthetic submitted text',
  )
  expect(screen.getByRole('button', { name: 'Send request' })).toBeDisabled()
  expect(
    screen.getByRole('link', {
      name: 'Review saved requests before sending again',
    }),
  ).toHaveAttribute('href', '/support')
  expect(request).toHaveBeenCalledTimes(1)
})

it('preserves a stale reply until an explicit discard and refresh', async () => {
  let latest = ticket
  handle = (path, init) => {
    if (init?.method === 'POST')
      throw new ApiError(409, 'Changed', 'SUPPORT_VERSION_CONFLICT')
    return path === '/support/tickets/ticket-one' ? latest : reads(path)
  }
  detail()
  fireEvent.change(await screen.findByLabelText('Your reply'), {
    target: { value: 'My unsent reply' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Send reply' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Your message has not been sent',
  )
  expect(screen.getByLabelText('Your reply')).toHaveValue('My unsent reply')
  expect(screen.getByRole('button', { name: 'Send reply' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Mark resolved' })).toBeDisabled()
  const mutation = vi
    .mocked(request)
    .mock.calls.find(([, init]) => init?.method === 'POST')!
  expect(JSON.parse(String(mutation[1]?.body))).toEqual({
    expected_version: 1,
    body: 'My unsent reply',
  })
  latest = { ...ticket, version: 2, status: 'in_progress' }
  fireEvent.click(
    screen.getByRole('button', { name: 'Reload latest conversation' }),
  )
  expect(await screen.findByLabelText('Your reply')).toHaveValue('')
  expect(screen.getByText('In progress', { exact: true })).toBeVisible()
})

it('requires clearing or sending a draft before resolving and allows reopening', async () => {
  let latest = ticket
  handle = (path, init) => {
    if (init?.method === 'POST') {
      latest = { ...ticket, status: 'resolved', version: 2 }
      return latest
    }
    return path === '/support/tickets/ticket-one' ? latest : reads(path)
  }
  detail()
  fireEvent.change(await screen.findByLabelText('Your reply'), {
    target: { value: 'Unsent' },
  })
  expect(screen.getByRole('button', { name: 'Mark resolved' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Clear draft' }))
  fireEvent.click(screen.getByRole('button', { name: 'Mark resolved' }))
  expect(
    await screen.findByRole('button', { name: 'Reopen request' }),
  ).toBeEnabled()
  expect(screen.queryByLabelText('Your reply')).not.toBeInTheDocument()
})

it('renders submitted markup as text without loading farms', async () => {
  detail()
  expect(await screen.findByText(messages.items[0].body)).toBeVisible()
  expect(document.querySelector('.support-messages b')).toBeNull()
  expect(
    vi.mocked(request).mock.calls.some(([path]) => path.startsWith('/farms')),
  ).toBe(false)
})

it('denies farmer access to the admin inbox before requesting its data', async () => {
  render(
    <MemoryRouter initialEntries={['/admin/support']}>
      <App />
    </MemoryRouter>,
  )
  expect(
    await screen.findByRole('heading', { name: 'Access denied' }),
  ).toBeVisible()
  expect(
    vi
      .mocked(request)
      .mock.calls.some(([path]) => path.startsWith('/admin/support')),
  ).toBe(false)
})

it('discards a late private ticket response after the account changes', async () => {
  let resolveOld!: (value: Ticket) => void
  let count = 0
  handle = (path) => {
    if (path === '/support/tickets/ticket-one') {
      if (++count === 1)
        return new Promise<Ticket>((resolve) => {
          resolveOld = resolve
        })
      throw new ApiError(404, 'Unavailable')
    }
    return reads(path)
  }
  render(
    <MemoryRouter initialEntries={['/support/ticket-one']}>
      <App />
    </MemoryRouter>,
  )
  await waitFor(() => expect(count).toBe(1))
  act(() =>
    window.dispatchEvent(
      new CustomEvent('account-session', {
        detail: { ...user, id: 'another-owner' },
      }),
    ),
  )
  expect(
    await screen.findByRole('heading', { name: 'Request unavailable' }),
  ).toBeVisible()
  await act(async () => resolveOld(ticket))
  expect(screen.queryByText(ticket.subject)).not.toBeInTheDocument()
})

it('keeps Help public and honestly shows an unconfigured contact channel', async () => {
  wrap(<HelpPage />, '/', null)
  expect(
    await screen.findByText(
      'A public support email has not been configured yet.',
      { exact: false },
    ),
  ).toBeVisible()
  expect(
    screen.getByRole('link', { name: 'Log in to send a request' }),
  ).toHaveAttribute('href', '/login')
  expect(
    vi.mocked(request).mock.calls.every(([path]) => path === '/help/contact'),
  ).toBe(true)
})
