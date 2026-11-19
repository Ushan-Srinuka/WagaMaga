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
  'does not load private farms for a signed-in %s on the public landing page',
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
      await screen.findByRole('link', { name: /Open my account/ }),
    ).toHaveAttribute('href', '/account')
    expect(
      screen.queryByRole('combobox', { name: 'Choose your farm' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: /Add my farm/ }),
    ).not.toBeInTheDocument()
    expect(
      vi.mocked(request).mock.calls.some(([path]) => path.startsWith('/farms')),
    ).toBe(false)
  },
)

it('shows a clear signed-out state and working account entry links', async () => {
  vi.mocked(restoreSession).mockRejectedValueOnce(
    new ApiError(401, 'Sign in to continue.'),
  )
  render(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>,
  )
  expect(await screen.findByText('You’re signed out')).toBeVisible()
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
    /Your farm\.\s*All in one place\./i,
  )
  expect(
    screen.getAllByRole('link', { name: 'Create account' })[0],
  ).toHaveAttribute('href', '/register')
  expect(screen.getAllByRole('link', { name: 'Log in' })[0]).toHaveAttribute(
    'href',
    '/login',
  )
  expect(screen.getAllByText('Planned', { exact: true })).toHaveLength(2)
  expect(screen.getByText('Available', { exact: true })).toBeVisible()
  expect(screen.getAllByText('Illustrative preview')).toHaveLength(3)
  for (const link of screen.getAllByRole('link')) {
    const href = link.getAttribute('href')
    if (href?.startsWith('#')) {
      expect(document.getElementById(href.slice(1))).not.toBeNull()
    }
  }
  expect(request).not.toHaveBeenCalled()
  expect(screen.getByRole('link', { name: /Get started/ })).toHaveAttribute(
    'href',
    '/register',
  )
})

it('shows the signed-in account and an unread notification link', async () => {
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
  expect(await screen.findByText('Synthetic Farmer')).toBeVisible()
  expect(
    screen.getAllByRole('link', { name: 'My account' })[0],
  ).toHaveAttribute('href', '/account')
  expect(
    await screen.findByRole('link', { name: 'Notifications, 3 unread' }),
  ).toHaveAttribute('href', '/notifications')
  expect(screen.getByRole('link', { name: 'My Farms' })).toHaveAttribute(
    'href',
    '/farms',
  )
  expect(
    await screen.findByRole('link', { name: /Add my farm/ }),
  ).toHaveAttribute('href', '/farms/new')
  expect(
    screen.getByRole('banner').querySelector('a[href="/farms/new"]'),
  ).toBeInTheDocument()
  expect(
    screen.queryByRole('link', { name: 'Dashboard' }),
  ).not.toBeInTheDocument()
})
