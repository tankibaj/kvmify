import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor, act } from '@testing-library/react'
import { renderWithProviders } from './utils'
import ProvisionForm from '../components/provision/ProvisionForm'

// ─── Mock api/client entirely ────────────────────────────────────────────────
const mockMutate = vi.fn()

vi.mock('../api/client', () => {
  return {
    useNetworks: () => ({
      data: [{ id: 'virbr0', label: 'default', mode: 'nat', is_default: true }],
      isLoading: false,
    }),
    usePools: () => ({
      data: [{ name: 'default', path: '/var/lib/libvirt/images', available: 50_000_000_000, is_default: true }],
      isLoading: false,
    }),
    useProvisionVM: () => ({
      mutate: mockMutate,
      isPending: false,
      isError: false,
      error: null,
    }),
  }
})

beforeEach(() => {
  mockMutate.mockReset()
})

// ─── helpers ─────────────────────────────────────────────────────────────────

function fillValidForm() {
  fireEvent.change(screen.getByLabelText(/vm name/i), {
    target: { value: 'my-test-vm' },
  })
  fireEvent.change(screen.getByPlaceholderText(/ssh-rsa/i), {
    target: { value: 'ssh-rsa AAAAB3NzaC1yc2EAAA test@host' },
  })
}

// ─── VM name validation ───────────────────────────────────────────────────────

describe('ProvisionForm — VM name validation', () => {
  it('shows error and blocks submit when name is empty', async () => {
    renderWithProviders(<ProvisionForm />)
    fireEvent.click(screen.getByText(/provision vm/i))
    await waitFor(() => {
      expect(screen.getByText(/vm name is required/i)).toBeInTheDocument()
    })
    expect(mockMutate).not.toHaveBeenCalled()
  })

  it('rejects uppercase letters in VM name', async () => {
    renderWithProviders(<ProvisionForm />)
    fireEvent.change(screen.getByLabelText(/vm name/i), {
      target: { value: 'MyVM' },
    })
    fireEvent.click(screen.getByText(/provision vm/i))
    await waitFor(() => {
      expect(screen.getByText(/lowercase letters, numbers, hyphens/i)).toBeInTheDocument()
    })
    expect(mockMutate).not.toHaveBeenCalled()
  })

  it('rejects names with spaces', async () => {
    renderWithProviders(<ProvisionForm />)
    fireEvent.change(screen.getByLabelText(/vm name/i), {
      target: { value: 'my vm' },
    })
    fireEvent.click(screen.getByText(/provision vm/i))
    await waitFor(() => {
      expect(screen.getByText(/lowercase letters, numbers, hyphens/i)).toBeInTheDocument()
    })
    expect(mockMutate).not.toHaveBeenCalled()
  })

  it('rejects names longer than 32 characters', async () => {
    renderWithProviders(<ProvisionForm />)
    fireEvent.change(screen.getByLabelText(/vm name/i), {
      target: { value: 'a'.repeat(33) },
    })
    fireEvent.click(screen.getByText(/provision vm/i))
    await waitFor(() => {
      expect(screen.getByText(/max 32 characters/i)).toBeInTheDocument()
    })
    expect(mockMutate).not.toHaveBeenCalled()
  })

  it('rejects names with leading hyphen', async () => {
    renderWithProviders(<ProvisionForm />)
    fireEvent.change(screen.getByLabelText(/vm name/i), {
      target: { value: '-myvm' },
    })
    fireEvent.click(screen.getByText(/provision vm/i))
    await waitFor(() => {
      expect(screen.getByText(/lowercase letters, numbers, hyphens/i)).toBeInTheDocument()
    })
  })

  it('accepts valid lowercase-hyphen-digit name', async () => {
    renderWithProviders(<ProvisionForm />)
    fillValidForm()
    fireEvent.click(screen.getByText(/provision vm/i))
    await waitFor(() => {
      expect(screen.queryByText(/vm name is required/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/lowercase letters/i)).not.toBeInTheDocument()
    })
  })
})

// ─── Static IP path ───────────────────────────────────────────────────────────

describe('ProvisionForm — static IP validation', () => {
  it('switching to Static and leaving IP empty blocks submit with errors banner', async () => {
    renderWithProviders(<ProvisionForm />)
    // Switch to Static mode
    fireEvent.click(screen.getByText(/static ip/i))
    // Fill the rest of form but leave static_ip empty
    fillValidForm()
    fireEvent.click(screen.getByText(/provision vm/i))
    await waitFor(() => {
      // The form sets submitted=true and errors are populated, which renders
      // the "Please fix the errors above" banner
      expect(screen.getByText(/please fix the errors above/i)).toBeInTheDocument()
    })
    // mutation must NOT have been called
    expect(mockMutate).not.toHaveBeenCalled()
  })
})

// ─── Happy path ───────────────────────────────────────────────────────────────

describe('ProvisionForm — happy path', () => {
  it('calls provision.mutate with correctly-shaped body on valid submit', async () => {
    renderWithProviders(<ProvisionForm />)

    // NetworkConfig auto-selects the default network via setTimeout(fn, 0).
    // Flush timers so form.network is set before we submit.
    await act(async () => {
      await new Promise(r => setTimeout(r, 10))
    })

    fillValidForm()
    fireEvent.click(screen.getByText(/provision vm/i))
    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledTimes(1)
    })
    const [payload] = mockMutate.mock.calls[0]
    expect(payload).toMatchObject({
      vm_name: 'my-test-vm',
      ubuntu_version: expect.any(String),
      cpu: expect.any(Number),
      ram_mb: expect.any(Number),
      disk_gb: expect.any(Number),
      network: 'virbr0',
      ip_mode: 'dhcp',
      storage_pool: 'default',
      ssh_public_key: 'ssh-rsa AAAAB3NzaC1yc2EAAA test@host',
    })
    // DHCP mode must NOT include static IP fields
    expect(payload.static_ip).toBeUndefined()
    expect(payload.subnet_mask).toBeUndefined()
    expect(payload.gateway).toBeUndefined()
    expect(payload.dns).toBeUndefined()
  })
})
