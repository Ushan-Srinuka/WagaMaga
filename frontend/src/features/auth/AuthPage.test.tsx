import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SessionContext } from '../../app/session-context'
import { registerAccount, signIn } from '../../lib/accounts'
import AuthPage from './AuthPage'

vi.mock('../../lib/accounts', () => ({
  registerAccount: vi.fn(),
  signIn: vi.fn(),
}))
const password = 'a synthetic growing season password 1!'
const setUser = vi.fn()
function show(register = false, loginPath = '/login') {
  return render(
    <SessionContext.Provider
      value={{ user: null, phase: 'ready', setUser, restore: vi.fn() }}
    >
      <MemoryRouter initialEntries={[register ? '/register' : loginPath]}>
        <Routes>
          <Route path="/" element={<p>Landing page opened</p>} />
          <Route path="/register" element={<AuthPage register />} />
          <Route path="/login" element={<AuthPage />} />
          <Route
            path="/knowledge/chilli"
            element={<p>Chilli question box opened</p>}
          />
          <Route path="/advisor" element={<p>Advisor inbox opened</p>} />
          <Route
            path="/admin/overview"
            element={<p>Admin overview opened</p>}
          />
        </Routes>
      </MemoryRouter>
    </SessionContext.Provider>,
  )
}
function fill(register = false) {
  if (register)
    fireEvent.change(screen.getByLabelText('Display name'), {
      target: { value: 'Synthetic farmer' },
    })
  fireEvent.change(screen.getByLabelText('Email address'), {
    target: { value: 'farmer@example.com' },
  })
  fireEvent.change(screen.getByLabelText('Password', { exact: true }), {
    target: { value: password },
  })
}
beforeEach(() => vi.clearAllMocks())
describe('account entry forms', () => {
  it('blocks mismatched confirmation and keeps passwords masked by default', async () => {
    show(true)
    fill(true)
    expect(screen.getByLabelText('Password', { exact: true })).toHaveAttribute(
      'type',
      'password',
    )
    fireEvent.change(screen.getByLabelText('Confirm password'), {
      target: { value: 'a different synthetic password' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Create account/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'passwords do not match',
    )
    expect(registerAccount).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Show password' }))
    expect(screen.getByLabelText('Password', { exact: true })).toHaveAttribute(
      'type',
      'text',
    )
  })
  it('registers only account inputs and returns to login without signing in', async () => {
    vi.mocked(registerAccount).mockResolvedValue({ message: 'Processed' })
    show(true)
    fill(true)
    const minimumPassword = 'Abcdef1!'
    fireEvent.change(screen.getByLabelText('Password', { exact: true }), {
      target: { value: minimumPassword },
    })
    fireEvent.change(screen.getByLabelText('Confirm password'), {
      target: { value: minimumPassword },
    })
    fireEvent.click(screen.getByRole('button', { name: /Create account/ }))
    expect(
      await screen.findByRole('heading', { name: 'Log in' }),
    ).toBeInTheDocument()
    expect(registerAccount).toHaveBeenCalledWith(
      'Synthetic farmer',
      'farmer@example.com',
      minimumPassword,
    )
    expect(signIn).not.toHaveBeenCalled()
    expect(screen.getByRole('status')).toHaveTextContent(
      'Registration request processed',
    )
  })
  it.each([
    ['too short', 'Abcd1!x'],
    ['missing letter', '1234567!'],
    ['missing number', 'abcdefg!'],
    ['missing symbol', 'abcdefg1'],
    ['space instead of symbol', 'Abcdef1 '],
    ['format character instead of symbol', 'Abcdef1\u200b'],
    ['too long', `${'a'.repeat(127)}1!`],
  ])(
    'rejects a signup password that is %s before sending it',
    async (_, invalid) => {
      show(true)
      fill(true)
      const input = screen.getByLabelText('Password', { exact: true })
      expect(input).toHaveAttribute('minlength', '8')
      expect(screen.getByLabelText('Confirm password')).toHaveAttribute(
        'minlength',
        '8',
      )
      fireEvent.change(input, { target: { value: invalid } })
      fireEvent.change(screen.getByLabelText('Confirm password'), {
        target: { value: invalid },
      })
      fireEvent.submit(input.closest('form')!)
      expect(await screen.findByRole('alert')).toHaveTextContent(
        'at least one letter, one number and one symbol',
      )
      expect(registerAccount).not.toHaveBeenCalled()
    },
  )
  it.each([
    'abcdef1!',
    'අbcdef1!',
    'Abcdef١!',
    'Abcdef1€',
    `${'a'.repeat(126)}1!`,
    ' abcd1! ',
  ])(
    'accepts supported password characters without trimming the value',
    async (valid) => {
      vi.mocked(registerAccount).mockResolvedValue({ message: 'Processed' })
      show(true)
      fill(true)
      fireEvent.change(screen.getByLabelText('Password', { exact: true }), {
        target: { value: valid },
      })
      fireEvent.change(screen.getByLabelText('Confirm password'), {
        target: { value: valid },
      })
      fireEvent.click(screen.getByRole('button', { name: /Create account/ }))
      await screen.findByRole('heading', { name: 'Log in' })
      expect(registerAccount).toHaveBeenCalledWith(
        'Synthetic farmer',
        'farmer@example.com',
        valid,
      )
    },
  )
  it('shows safe login errors and permits retry', async () => {
    vi.mocked(signIn).mockRejectedValueOnce(
      new Error('Email or password is incorrect.'),
    )
    vi.mocked(signIn).mockResolvedValueOnce({
      access_token: 'synthetic-token',
      expires_in: 900,
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
    })
    show()
    fill()
    const legacyPassword = 'a synthetic growing season password'
    fireEvent.change(screen.getByLabelText('Password', { exact: true }), {
      target: { value: legacyPassword },
    })
    fireEvent.click(screen.getByRole('button', { name: /Sign in/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Email or password is incorrect.',
    )
    expect(signIn).toHaveBeenCalledWith('farmer@example.com', legacyPassword)
    fireEvent.click(screen.getByRole('button', { name: /Sign in/ }))
    expect(await screen.findByText('Landing page opened')).toBeInTheDocument()
    await waitFor(() => expect(setUser).toHaveBeenCalled())
  })
  it.each(['farmer', 'administrator', 'advisor'] as const)(
    'routes Log in to ask to the right screen for %s',
    async (role) => {
      vi.mocked(signIn).mockResolvedValueOnce({
        access_token: 'synthetic',
        expires_in: 900,
        user: {
          id: 'other-role',
          email: 'farmer@example.com',
          display_name: 'Synthetic account',
          role,
          disabled_at: null,
          deleted_at: null,
          version: 1,
          created_at: '2026-11-19T00:00:00Z',
        },
      })
      show(false, '/login?ask=chilli')
      fill()
      fireEvent.click(screen.getByRole('button', { name: /Sign in/ }))
      expect(
        await screen.findByText(
          role === 'administrator'
            ? 'Admin overview opened'
            : role === 'advisor'
              ? 'Advisor inbox opened'
              : 'Chilli question box opened',
        ),
      ).toBeInTheDocument()
      expect(screen.queryByText('Landing page opened')).not.toBeInTheDocument()
    },
  )
})
