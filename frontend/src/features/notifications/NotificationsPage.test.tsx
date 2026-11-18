import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { request } from '../../lib/accounts'
import type { Notification, NotificationPage } from '../../lib/notifications'
import NotificationsPage from './NotificationsPage'

const item: Notification = {
  id: 'notice-1',
  event_type: 'role_changed',
  title: 'Account role updated',
  body: 'Your WagaMaga account role is now advisor.',
  created_at: '2026-11-18T00:00:00Z',
  read_at: null,
}
const page: NotificationPage = {
  items: [item],
  total: 1,
  unread_count: 1,
  page: 1,
  page_size: 20,
}

vi.mock('../../lib/accounts', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/accounts')>()),
  request: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())

it('shows a private account update and lets its recipient mark it read', async () => {
  vi.mocked(request)
    .mockResolvedValueOnce(page)
    .mockResolvedValueOnce({ ...item, read_at: '2026-11-18T01:00:00Z' })
  render(
    <MemoryRouter>
      <NotificationsPage />
    </MemoryRouter>,
  )
  expect(
    await screen.findByText('Your WagaMaga account role is now advisor.'),
  ).toBeVisible()
  expect(screen.getByText('1 unread')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Mark read' }))
  expect(
    await screen.findByRole('button', { name: 'Mark unread' }),
  ).toBeVisible()
  expect(screen.getByText('0 unread')).toBeVisible()
  expect(request).toHaveBeenLastCalledWith('/notifications/notice-1', {
    method: 'PATCH',
    body: JSON.stringify({ read: true }),
  })
})
