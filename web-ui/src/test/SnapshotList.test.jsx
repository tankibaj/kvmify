import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { renderWithProviders } from './utils'
import SnapshotList from '../components/vm/SnapshotList'

// ─── Mock api/client ──────────────────────────────────────────────────────────

const mockExportMutate = vi.fn()

vi.mock('../api/client', () => ({
  useVMSnapshots: () => ({
    data: [
      {
        name: 'snap-20240101-1200',
        description: 'Before upgrade',
        created: '2024-01-01T12:00:00Z',
        is_current: true,
        state: 'shutoff',
      },
    ],
    isLoading: false,
  }),
  useCreateSnapshot: () => ({ mutate: vi.fn(), isPending: false }),
  useRestoreSnapshot: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteSnapshot: () => ({ mutate: vi.fn(), isPending: false }),
  useExportTemplate: () => ({ mutate: mockExportMutate, isPending: false }),
}))

beforeEach(() => {
  mockExportMutate.mockReset()
})

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('SnapshotList — Export action', () => {
  it('renders an Export button for a snapshot', () => {
    renderWithProviders(<SnapshotList vmName="my-vm" />)
    expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument()
  })

  it('clicking Export opens the export modal', async () => {
    renderWithProviders(<SnapshotList vmName="my-vm" />)
    fireEvent.click(screen.getByRole('button', { name: /^export$/i }))
    await waitFor(() => {
      expect(screen.getByText(/export snapshot as template/i)).toBeInTheDocument()
    })
  })

  it('Export Template button is disabled for an empty/invalid template name', async () => {
    renderWithProviders(<SnapshotList vmName="my-vm" />)
    fireEvent.click(screen.getByRole('button', { name: /^export$/i }))
    await waitFor(() => {
      expect(screen.getByText(/export snapshot as template/i)).toBeInTheDocument()
    })
    // The modal footer Export Template button — name is empty by default → disabled
    const exportBtn = screen.getByRole('button', { name: /export template/i })
    expect(exportBtn).toBeDisabled()
  })

  it('Export Template button is disabled for an invalid name (uppercase)', async () => {
    renderWithProviders(<SnapshotList vmName="my-vm" />)
    fireEvent.click(screen.getByRole('button', { name: /^export$/i }))
    await waitFor(() => {
      expect(screen.getByText(/export snapshot as template/i)).toBeInTheDocument()
    })
    const input = screen.getByPlaceholderText(/my-template-name/i)
    fireEvent.change(input, { target: { value: 'InvalidName' } })
    const exportBtn = screen.getByRole('button', { name: /export template/i })
    expect(exportBtn).toBeDisabled()
  })

  it('Export Template button is enabled for a valid name', async () => {
    renderWithProviders(<SnapshotList vmName="my-vm" />)
    fireEvent.click(screen.getByRole('button', { name: /^export$/i }))
    await waitFor(() => {
      expect(screen.getByText(/export snapshot as template/i)).toBeInTheDocument()
    })
    const input = screen.getByPlaceholderText(/my-template-name/i)
    fireEvent.change(input, { target: { value: 'my-valid-template' } })
    const exportBtn = screen.getByRole('button', { name: /export template/i })
    expect(exportBtn).not.toBeDisabled()
  })
})
