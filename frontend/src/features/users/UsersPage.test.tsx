import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it, vi } from 'vitest'
import { ApiError, request } from '../../lib/accounts'
import UsersPage from './UsersPage'

vi.mock('../../lib/accounts', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/accounts')>()),
  request: vi.fn(),
}))

it('shows a rate-limit error, supports retry, then shows the empty result', async () => {
  vi.mocked(request)
    .mockRejectedValueOnce(
      new ApiError(429, 'Too many attempts. Please try again later.'),
    )
    .mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 20 })
  render(
    <MemoryRouter>
      <UsersPage />
    </MemoryRouter>,
  )
  expect(screen.getByRole('status')).toHaveTextContent('Loading')
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Too many attempts',
  )
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('No accounts found.')).toBeInTheDocument()
})

it('offers a deleted-account filter', () => {
  vi.mocked(request).mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
  })
  render(
    <MemoryRouter>
      <UsersPage />
    </MemoryRouter>,
  )
  fireEvent.change(screen.getByLabelText('Status'), {
    target: { value: 'deleted' },
  })
  expect(screen.getByLabelText('Status')).toHaveValue('deleted')
})
