import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

describe('foundation connectivity', () => {
  it('shows API availability separately from database readiness', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ status: 'ok' }), { status: 200 }),
        )
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ status: 'not_ready' }), {
            status: 503,
          }),
        ),
    )
    render(<App />)
    expect(await screen.findByText('Connected')).toBeInTheDocument()
    expect(screen.getByText('Not ready')).toBeInTheDocument()
    expect(screen.getByText(/API is running/)).toBeInTheDocument()
  })

  it('recovers from a failed connection when the user retries', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error('offline'))
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'could not be reached',
    )
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: 'ok' }), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ status: 'ready' }), { status: 200 }),
      )
    fireEvent.click(screen.getByRole('button', { name: 'Check connection' }))
    expect(await screen.findByText('Ready')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
