import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it, vi } from 'vitest'
import { request } from '../../lib/accounts'
import AuditPage from './AuditPage'

vi.mock('../../lib/accounts', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/accounts')>()),
  request: vi.fn(),
}))

it('shows an administrator audit record without exposing account email fields', async () => {
  vi.mocked(request).mockResolvedValueOnce({
    items: [
      {
        id: 'audit-1',
        actor_id: 'actor-1',
        actor_name: 'Synthetic admin',
        target_id: 'target-1',
        target_name: 'Synthetic advisor',
        action: 'role',
        previous_value: 'farmer',
        new_value: 'advisor',
        reason: 'Synthetic account setup',
        request_id: 'request-1',
        created_at: '2026-11-18T00:00:00Z',
      },
    ],
    total: 1,
    page: 1,
    page_size: 25,
  })
  render(
    <MemoryRouter>
      <AuditPage />
    </MemoryRouter>,
  )
  expect(await screen.findByText('Synthetic account setup')).toBeVisible()
  expect(screen.getByText('Synthetic advisor')).toBeVisible()
  expect(screen.getByText('farmer → advisor')).toBeVisible()
  expect(screen.queryByText(/@example\.com/)).not.toBeInTheDocument()
  expect(screen.getByText('Viewing this history is recorded.')).toBeVisible()
})
