import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { renderWithProviders } from './utils'
import Images from '../pages/Images'

// ─── Mock api/client ──────────────────────────────────────────────────────────

const mockDeleteTemplateMutate = vi.fn()

vi.mock('../api/client', () => ({
  useImages: () => ({
    data: [
      {
        version: '2204',
        label: 'Ubuntu 22.04',
        codename: 'jammy',
        size: 2_147_483_648,
        last_updated: '2024-01-01T00:00:00Z',
        checksum: 'abc123def456abc123def456',
        status: 'up_to_date',
      },
    ],
    isLoading: false,
    error: null,
  }),
  useSyncImages: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useTemplates: () => ({
    data: [
      {
        name: 'my-template',
        size: 3_221_225_472,
        created: '2024-06-01T10:00:00Z',
        source_vm: 'dev-vm',
        source_snapshot: 'snap-001',
        os_variant: 'ubuntu22.04',
      },
    ],
  }),
  useDeleteTemplate: () => ({
    mutate: mockDeleteTemplateMutate,
    isPending: false,
  }),
  useAddImage: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useDeleteImage: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}))

// The sync status query is issued directly via useQuery inside Images — mock fetch
beforeEach(() => {
  mockDeleteTemplateMutate.mockReset()
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ state: 'idle', log: null }),
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

function renderImages() {
  return renderWithProviders(
    <MemoryRouter>
      <Images />
    </MemoryRouter>
  )
}

// ─── VM Templates section ─────────────────────────────────────────────────────

describe('Images page — VM Templates section', () => {
  it('renders the VM Templates heading', () => {
    renderImages()
    expect(screen.getByText('VM Templates')).toBeInTheDocument()
  })

  it('lists the template name in the table', () => {
    renderImages()
    expect(screen.getByText('my-template')).toBeInTheDocument()
  })

  it('shows source VM and snapshot in the Source column', () => {
    renderImages()
    expect(screen.getByText('dev-vm @ snap-001')).toBeInTheDocument()
  })

  it('does not show the empty-state message when templates are present', () => {
    renderImages()
    expect(
      screen.queryByText(/no templates yet/i)
    ).not.toBeInTheDocument()
  })

  it('clicking Delete opens a confirm modal', async () => {
    renderImages()
    // Find the Delete button in the templates section
    const deleteBtn = screen.getByRole('button', { name: /delete/i })
    fireEvent.click(deleteBtn)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /delete template/i })).toBeInTheDocument()
      expect(screen.getByText(/cannot be undone/i)).toBeInTheDocument()
    })
  })
})
