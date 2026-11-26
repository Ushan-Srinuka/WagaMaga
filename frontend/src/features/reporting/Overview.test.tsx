import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../../App'
import { SessionContext } from '../../app/session-context'
import { ApiError, request, type Account } from '../../lib/accounts'
import OverviewPage, {
  FarmerRecordSummary,
  type FarmerSummary,
  type Overview,
} from './OverviewPage'

const admin: Account = {
  id: 'synthetic-admin',
  role: 'administrator',
  email: 'admin@example.com',
  display_name: 'Synthetic administrator',
  disabled_at: null,
  deleted_at: null,
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
}
const empty = { total: 0, active: 0, archived: 0 }
const report: Overview = {
  generated_at: '2026-11-19T00:00:00Z',
  accounts: {
    total: 1,
    enabled: 1,
    disabled: 0,
    farmers: 0,
    advisors: 0,
    administrators: 1,
    new_farmers_30_days: 0,
    removed: 0,
  },
  farms: empty,
  cultivations: empty,
  support: { total: 0, open: 0, in_progress: 0, resolved: 0 },
}
vi.mock('../../lib/accounts', async (original) => ({
  ...(await original<typeof import('../../lib/accounts')>()),
  request: vi.fn(),
  restoreSession: vi.fn().mockImplementation(async () => ({
    user: admin,
    access_token: 'synthetic',
    expires_in: 900,
  })),
}))
let handle: (path: string) => unknown
beforeEach(() => {
  vi.clearAllMocks()
  handle = (path) =>
    path.startsWith('/notifications')
      ? { unread_count: 0, items: [], total: 0, page: 1, page_size: 20 }
      : report
  vi.mocked(request).mockImplementation(
    async <T,>(path: string) => (await handle(path)) as T,
  )
})
function wrap(element: React.ReactNode) {
  return render(
    <MemoryRouter>
      <SessionContext.Provider
        value={{
          user: admin,
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

it('shows real zero counts and definitions without inventing activity metrics', async () => {
  wrap(<OverviewPage />)
  expect(screen.getByRole('status')).toHaveTextContent('Loading')
  const highlights = await screen.findByRole('region', {
    name: 'Administration summary',
  })
  expect(within(highlights).getAllByRole('article')).toHaveLength(4)
  expect(highlights).toHaveTextContent('0 new in the last 30 days')
  expect(
    screen.getByText('Enabled means access is allowed;', { exact: false }),
  ).toBeVisible()
  expect(screen.queryByText('Active users')).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Manage farmers' })).toHaveAttribute(
    'href',
    '/admin/users?role=farmer',
  )
  expect(
    vi.mocked(request).mock.calls.some(([path]) => path.startsWith('/farms')),
  ).toBe(false)
})

it('does not show zero or stale totals when the overview fails and supports retry', async () => {
  handle = () => {
    throw new ApiError(503, 'Unavailable')
  }
  wrap(<OverviewPage />)
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'No counts are shown',
  )
  expect(
    screen.queryByRole('region', { name: 'Administration summary' }),
  ).not.toBeInTheDocument()
  handle = () => report
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(
    await screen.findByRole('region', { name: 'Administration summary' }),
  ).toBeVisible()
})

it('ignores a late per-farmer response when the target account changes', async () => {
  let finishOld!: (value: FarmerSummary) => void
  handle = (path) =>
    path.includes('first-farmer')
      ? new Promise<FarmerSummary>((resolve) => {
          finishOld = resolve
        })
      : {
          user_id: 'second-farmer',
          generated_at: report.generated_at,
          farms: { total: 1, active: 1, archived: 0 },
          cultivations: empty,
        }
  const first = render(
    <MemoryRouter>
      <FarmerRecordSummary userId="first-farmer" />
    </MemoryRouter>,
  )
  await waitFor(() => expect(finishOld).toBeDefined())
  first.rerender(
    <MemoryRouter>
      <FarmerRecordSummary userId="second-farmer" />
    </MemoryRouter>,
  )
  await waitFor(() =>
    expect(screen.queryByRole('status')).not.toBeInTheDocument(),
  )
  await act(async () =>
    finishOld({
      user_id: 'first-farmer',
      generated_at: report.generated_at,
      farms: { total: 9876, active: 9876, archived: 0 },
      cultivations: empty,
    }),
  )
  expect(screen.queryByText('9876')).not.toBeInTheDocument()
  expect(
    vi
      .mocked(request)
      .mock.calls.every(([path]) => path.endsWith('/farm-summary')),
  ).toBe(true)
})

it('denies non-admin overview navigation before fetching counts', async () => {
  const { restoreSession } = await import('../../lib/accounts')
  vi.mocked(restoreSession).mockResolvedValueOnce({
    user: { ...admin, role: 'farmer' },
    access_token: 'synthetic',
    expires_in: 900,
  })
  render(
    <MemoryRouter initialEntries={['/admin/overview']}>
      <App />
    </MemoryRouter>,
  )
  expect(
    await screen.findByRole('heading', { name: 'Access denied' }),
  ).toBeVisible()
  expect(
    vi.mocked(request).mock.calls.some(([path]) => path === '/admin/overview'),
  ).toBe(false)
})

it('clears rendered report values when a refreshed session is revoked', async () => {
  render(
    <MemoryRouter initialEntries={['/admin/overview']}>
      <App />
    </MemoryRouter>,
  )
  expect(
    await screen.findByRole('region', { name: 'Administration summary' }),
  ).toBeVisible()
  handle = () => {
    throw new ApiError(401, 'Revoked')
  }
  fireEvent.click(screen.getByRole('button', { name: 'Refresh overview' }))
  expect(await screen.findByRole('heading', { name: 'Log in' })).toBeVisible()
  expect(
    screen.queryByRole('region', { name: 'Administration summary' }),
  ).not.toBeInTheDocument()
})
