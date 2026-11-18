import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import AccountPage from './AccountPage'
import { request } from '../../lib/accounts'

const account = {
  id: 'synthetic-user-id',
  display_name: 'Synthetic farmer',
  email: 'farmer@example.com',
  role: 'farmer' as const,
  disabled_at: null,
  deleted_at: null,
  version: 1,
  created_at: '2026-11-16T00:00:00Z',
}

vi.mock('../../app/session-context', () => ({
  useSession: () => ({ user: account, setUser: vi.fn() }),
}))
vi.mock('../../lib/accounts', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/accounts')>()),
  request: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())

it('validates matching password policy and submits the current password securely', async () => {
  vi.mocked(request).mockResolvedValueOnce(account)
  render(<AccountPage />)
  fireEvent.change(screen.getByLabelText('Current password'), {
    target: { value: 'old synthetic password' },
  })
  fireEvent.change(screen.getByLabelText('New password'), {
    target: { value: 'new synthetic password' },
  })
  fireEvent.change(screen.getByLabelText('Confirm new password'), {
    target: { value: 'new synthetic password' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Change password' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'at least one letter',
  )
  expect(request).not.toHaveBeenCalled()

  fireEvent.change(screen.getByLabelText('New password'), {
    target: { value: 'new!letter123' },
  })
  fireEvent.change(screen.getByLabelText('Confirm new password'), {
    target: { value: 'new!letter123' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Change password' }))
  expect(await screen.findByRole('status')).toHaveTextContent(
    'Password changed',
  )
  expect(request).toHaveBeenCalledWith('/me/password', {
    method: 'POST',
    body: JSON.stringify({
      current_password: 'old synthetic password',
      new_password: 'new!letter123',
    }),
  })
})
