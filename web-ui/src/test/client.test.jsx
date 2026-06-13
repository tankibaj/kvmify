import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { NotificationProvider } from '../contexts/NotificationContext'
import { makeQueryClient } from './utils'

// We test the exported hooks and the internal apiFetch behaviour by spying on
// global fetch — no real network calls are made.

// Dynamically import the module after each fetch mock so we exercise real code.
// Since vitest hoists vi.mock, we instead use vi.spyOn(globalThis, 'fetch').

// ─── helpers ─────────────────────────────────────────────────────────────────

function makeFetchResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: () => Promise.resolve(body),
  })
}

function wrapper() {
  const queryClient = makeQueryClient()
  return function Wrap({ children }) {
    return (
      <QueryClientProvider client={queryClient}>
        <NotificationProvider>{children}</NotificationProvider>
      </QueryClientProvider>
    )
  }
}

// ─── apiFetch behaviour (via useVMs which calls apiFetch('/vms')) ─────────────

describe('apiFetch — via useVMs hook', () => {
  let fetchSpy

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, 'fetch')
  })

  afterEach(() => {
    fetchSpy.mockRestore()
  })

  it('calls /api/vms with correct headers', async () => {
    fetchSpy.mockReturnValue(makeFetchResponse([]))
    const { useVMs } = await import('../api/client')

    const { result } = renderHook(() => useVMs(), { wrapper: wrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/vms',
      expect.objectContaining({
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      })
    )
  })

  it('returns parsed JSON on 200 response', async () => {
    const fakeVMs = [{ name: 'vm-1', state: 'running' }]
    fetchSpy.mockReturnValue(makeFetchResponse(fakeVMs))
    const { useVMs } = await import('../api/client')

    const { result } = renderHook(() => useVMs(), { wrapper: wrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(fakeVMs)
  })

  it('throws with parsed detail message on non-2xx response', async () => {
    fetchSpy.mockReturnValue(makeFetchResponse({ detail: 'Forbidden' }, 403))
    const { useVMs } = await import('../api/client')

    const { result } = renderHook(() => useVMs(), { wrapper: wrapper() })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error?.message).toBe('Forbidden')
  })
})

// ─── apiFetch body serialisation (via useSyncImages mutation) ─────────────────

describe('useSyncImages mutation', () => {
  let fetchSpy

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, 'fetch')
  })

  afterEach(() => {
    fetchSpy.mockRestore()
  })

  it('POSTs to /api/images/sync with JSON-encoded version body', async () => {
    fetchSpy.mockReturnValue(makeFetchResponse({ status: 'started' }))
    const { useSyncImages } = await import('../api/client')

    const { result } = renderHook(() => useSyncImages(), { wrapper: wrapper() })

    result.current.mutate('2404')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/images/sync',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ version: '2404' }),
      })
    )
  })

  it('POSTs empty body when no version provided', async () => {
    fetchSpy.mockReturnValue(makeFetchResponse({ status: 'started' }))
    const { useSyncImages } = await import('../api/client')

    const { result } = renderHook(() => useSyncImages(), { wrapper: wrapper() })

    result.current.mutate(undefined)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/images/sync',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({}),
      })
    )
  })

  it('falls back to statusText when error response body has no detail', async () => {
    // Simulate a JSON parse failure on the error response
    fetchSpy.mockReturnValue(
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.reject(new Error('bad json')),
      })
    )
    const { useSyncImages } = await import('../api/client')

    const { result } = renderHook(() => useSyncImages(), { wrapper: wrapper() })

    result.current.mutate('2404')

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error?.message).toBe('Internal Server Error')
  })
})
