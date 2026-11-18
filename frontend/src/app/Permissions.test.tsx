import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it, vi } from 'vitest'
import App from '../App'
import { request } from '../lib/accounts'

vi.mock('../lib/accounts', async (importOriginal) => {
  const original = await importOriginal<typeof import('../lib/accounts')>()
  return {
    ...original,
    request: vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      unread_count: 0,
      page: 1,
      page_size: 1,
    }),
    restoreSession: vi.fn().mockResolvedValue({
      access_token: 'synthetic-token',
      user: {
        id: 'one',
        email: 'farmer@example.com',
        display_name: 'Farmer',
        role: 'farmer',
        disabled_at: null,
        deleted_at: null,
        version: 1,
        created_at: '2026-11-16T00:00:00Z',
      },
    }),
  }
})

it('denies a farmer visiting an administrator URL without requesting other accounts', async () => {
  render(
    <MemoryRouter initialEntries={['/admin/users']}>
      <App />
    </MemoryRouter>,
  )
  expect(
    await screen.findByRole('heading', { name: 'Access denied' }),
  ).toBeInTheDocument()
  expect(request).not.toHaveBeenCalledWith('/admin/users')
  expect(request).not.toHaveBeenCalledWith('/admin/audit-logs')
  expect(
    screen.queryByRole('link', { name: 'User management' }),
  ).not.toBeInTheDocument()
})
