import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../../App'
import { ApiError, request, restoreSession } from '../../lib/accounts'

vi.mock('../../lib/accounts', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/accounts')>()),
  request: vi.fn(),
  restoreSession: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())

it.each(['advisor', 'administrator'] as const)(
  'keeps farmer questions and private farms out of the %s homepage actions',
  async (role) => {
    vi.mocked(restoreSession).mockResolvedValueOnce({
      access_token: 'synthetic',
      expires_in: 900,
      user: {
        id: 'other-role',
        display_name: 'Synthetic account',
        email: 'other@example.test',
        role,
        disabled_at: null,
        deleted_at: null,
        version: 1,
        created_at: '2026-11-19T00:00:00Z',
      },
    })
    vi.mocked(request).mockResolvedValue({ unread_count: 0 })
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )
    expect(
      await screen.findByRole('link', { name: 'My account' }),
    ).toHaveAttribute('href', '/account')
    expect(
      screen.queryByRole('combobox', { name: 'Choose your farm' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: /Add my farm/ }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'Ask Chilli AI' }),
    ).not.toBeInTheDocument()
    expect(
      vi.mocked(request).mock.calls.some(([path]) => path.startsWith('/farms')),
    ).toBe(false)
  },
)

it('offers general login and a direct login for chilli questions', async () => {
  vi.mocked(restoreSession).mockRejectedValueOnce(
    new ApiError(401, 'Sign in to continue.'),
  )
  render(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>,
  )
  expect(
    await screen.findByRole('link', { name: 'Log in to ask' }),
  ).toHaveAttribute('href', '/login?ask=chilli')
  expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute(
    'href',
    '/login',
  )
  expect(screen.getByRole('link', { name: 'Create account' })).toHaveAttribute(
    'href',
    '/register',
  )
  expect(
    screen.getByRole('link', { name: 'Sign in for Chilli AI' }),
  ).toHaveAttribute('href', '/login?ask=chilli')
  expect(
    screen.getByRole('link', { name: 'Log in to view farms' }),
  ).toHaveAttribute('href', '/login')
  for (const link of screen.getAllByRole('link')) {
    const href = link.getAttribute('href')
    if (href?.startsWith('#')) {
      expect(document.getElementById(href.slice(1))).not.toBeNull()
    }
  }
  expect(request).not.toHaveBeenCalled()
})

it('offers chilli questions and farm actions to the signed-in farmer', async () => {
  vi.mocked(restoreSession).mockResolvedValueOnce({
    access_token: 'synthetic-token',
    expires_in: 900,
    user: {
      id: 'farmer-1',
      email: 'farmer@example.test',
      display_name: 'Synthetic Farmer',
      role: 'farmer',
      disabled_at: null,
      deleted_at: null,
      version: 1,
      created_at: '2026-11-18T00:00:00Z',
    },
  })
  vi.mocked(request).mockImplementation(
    async <T,>(path: string) =>
      (path.startsWith('/notifications')
        ? { unread_count: 3 }
        : { items: [], total: 0, page: 1, page_size: 100 }) as T,
  )
  render(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>,
  )
  expect(await screen.findByText('Hello, Synthetic Farmer')).toBeVisible()
  expect(
    screen.getAllByRole('link', { name: 'My account' })[0],
  ).toHaveAttribute('href', '/account')
  const notifications = await screen.findByRole('link', {
    name: 'Notifications, 3 unread',
  })
  expect(notifications).toHaveAttribute('href', '/notifications')
  expect(notifications).toHaveTextContent(/^3$/)
  expect(screen.getByRole('link', { name: 'My Farms' })).toHaveAttribute(
    'href',
    '/farms',
  )
  expect(screen.getByRole('link', { name: 'Ask Chilli AI' })).toHaveAttribute(
    'href',
    '/knowledge/chilli',
  )
  expect(
    screen.getByRole('link', { name: 'Add a field note' }),
  ).toHaveAttribute('href', '/field-notes/new')
  expect(screen.getByRole('link', { name: 'Planner' })).toHaveAttribute(
    'href',
    '/planner',
  )
  expect(
    screen.getByRole('link', { name: 'Ask a chilli question' }),
  ).toHaveAttribute('href', '/knowledge/chilli')
  expect(screen.getByRole('link', { name: 'View farms' })).toHaveAttribute(
    'href',
    '/farms',
  )
  expect(screen.getByRole('link', { name: 'Write a note' })).toHaveAttribute(
    'href',
    '/field-notes/new',
  )
  expect(screen.getByRole('link', { name: 'View tasks' })).toHaveAttribute(
    'href',
    '/planner',
  )
  expect(screen.getByRole('link', { name: 'Contact support' })).toHaveAttribute(
    'href',
    '/support/new',
  )
})

it('keeps the homepage readable when the session cannot be checked', async () => {
  vi.mocked(restoreSession).mockRejectedValueOnce(
    new ApiError(503, 'Service unavailable.'),
  )
  render(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>,
  )
  expect(await screen.findByRole('button', { name: 'Retry' })).toBeVisible()
  expect(
    screen.getByRole('heading', { name: 'Ask Chilli AI', level: 1 }),
  ).toBeVisible()
  expect(
    screen.queryByRole('link', { name: 'Ask Chilli AI' }),
  ).not.toBeInTheDocument()
  expect(request).not.toHaveBeenCalled()
})
