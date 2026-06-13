import React from 'react'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { NotificationProvider } from '../contexts/NotificationContext'

/**
 * Creates a fresh QueryClient per test (retry: false prevents hanging retries in tests).
 */
export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

/**
 * Render helper that wraps ui in QueryClientProvider + NotificationProvider.
 * A fresh QueryClient is created per call so tests don't share cache state.
 */
export function renderWithProviders(ui, options = {}) {
  const queryClient = options.queryClient ?? makeQueryClient()

  function Wrapper({ children }) {
    return (
      <QueryClientProvider client={queryClient}>
        <NotificationProvider>{children}</NotificationProvider>
      </QueryClientProvider>
    )
  }

  return { queryClient, ...render(ui, { wrapper: Wrapper, ...options }) }
}
