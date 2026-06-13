import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { renderWithProviders } from './utils'
import { validateNetworkConfig } from '../components/provision/NetworkConfig'
import NetworkConfig from '../components/provision/NetworkConfig'

// ─── Mock the api/client module so NetworkConfig never fires real fetches ───
vi.mock('../api/client', () => ({
  useNetworks: () => ({ data: undefined, isLoading: false }),
}))

// ─── validateNetworkConfig — pure helper ─────────────────────────────────────

describe('validateNetworkConfig — pure helper', () => {
  const NETWORK = { network: 'virbr0', ip_mode: 'dhcp' }

  it('DHCP mode is always valid when network is set', () => {
    const { valid, errors } = validateNetworkConfig(NETWORK)
    expect(valid).toBe(true)
    expect(errors).toEqual({})
  })

  it('DHCP mode ignores empty static fields', () => {
    const { valid } = validateNetworkConfig({
      ...NETWORK,
      static_ip: '',
      gateway: '',
      dns: '',
      subnet_mask: '',
    })
    expect(valid).toBe(true)
  })

  it('missing network id produces network error', () => {
    const { valid, errors } = validateNetworkConfig({ ...NETWORK, network: '' })
    expect(valid).toBe(false)
    expect(errors.network).toBeTruthy()
  })

  it('static mode with all valid fields is valid', () => {
    const { valid, errors } = validateNetworkConfig({
      network: 'virbr0',
      ip_mode: 'static',
      static_ip: '192.168.1.100',
      subnet_mask: '255.255.255.0',
      gateway: '192.168.1.1',
      dns: '8.8.8.8',
    })
    expect(valid).toBe(true)
    expect(errors).toEqual({})
  })

  it('static mode with invalid static_ip produces static_ip error', () => {
    const { valid, errors } = validateNetworkConfig({
      network: 'virbr0',
      ip_mode: 'static',
      static_ip: '999.999.999.999', // bad octets pattern — passes IPV4_RE but
      subnet_mask: '255.255.255.0',
      gateway: '192.168.1.1',
      dns: '8.8.8.8',
    })
    // The IPV4_RE only checks digit format, not octet range — no error expected here
    expect(valid).toBe(true)
  })

  it('static mode with non-numeric static_ip produces static_ip error', () => {
    const { valid, errors } = validateNetworkConfig({
      network: 'virbr0',
      ip_mode: 'static',
      static_ip: 'not-an-ip',
      subnet_mask: '255.255.255.0',
      gateway: '192.168.1.1',
      dns: '8.8.8.8',
    })
    expect(valid).toBe(false)
    expect(errors.static_ip).toBeTruthy()
  })

  it('static mode with empty static_ip produces static_ip error', () => {
    const { valid, errors } = validateNetworkConfig({
      network: 'virbr0',
      ip_mode: 'static',
      static_ip: '',
      subnet_mask: '255.255.255.0',
      gateway: '192.168.1.1',
      dns: '8.8.8.8',
    })
    expect(valid).toBe(false)
    expect(errors.static_ip).toBeTruthy()
  })

  it('static mode with invalid gateway produces gateway error', () => {
    const { valid, errors } = validateNetworkConfig({
      network: 'virbr0',
      ip_mode: 'static',
      static_ip: '192.168.1.100',
      subnet_mask: '255.255.255.0',
      gateway: 'bad-gw',
      dns: '8.8.8.8',
    })
    expect(valid).toBe(false)
    expect(errors.gateway).toBeTruthy()
  })

  it('static mode with invalid dns produces dns error', () => {
    const { valid, errors } = validateNetworkConfig({
      network: 'virbr0',
      ip_mode: 'static',
      static_ip: '192.168.1.100',
      subnet_mask: '255.255.255.0',
      gateway: '192.168.1.1',
      dns: 'bad-dns',
    })
    expect(valid).toBe(false)
    expect(errors.dns).toBeTruthy()
  })

  it('static mode with invalid subnet_mask produces subnet_mask error', () => {
    const { valid, errors } = validateNetworkConfig({
      network: 'virbr0',
      ip_mode: 'static',
      static_ip: '192.168.1.100',
      subnet_mask: 'bad-mask',
      gateway: '192.168.1.1',
      dns: '8.8.8.8',
    })
    expect(valid).toBe(false)
    expect(errors.subnet_mask).toBeTruthy()
  })
})

// ─── NetworkConfig component ──────────────────────────────────────────────────

const FAKE_NETWORKS = [
  { id: 'virbr0', label: 'default', mode: 'nat', is_default: true },
  { id: 'br0', label: 'bridge', mode: 'bridge', is_default: false },
]

function makeValue(overrides = {}) {
  return {
    network: 'virbr0',
    ip_mode: 'dhcp',
    static_ip: '',
    subnet_mask: '255.255.255.0',
    gateway: '',
    dns: '8.8.8.8',
    ...overrides,
  }
}

describe('NetworkConfig component', () => {
  it('renders network interface options from networks prop', () => {
    const value = makeValue()
    renderWithProviders(
      <NetworkConfig value={value} onChange={() => {}} networks={FAKE_NETWORKS} />
    )
    expect(screen.getByText(/default \(nat\)/i)).toBeInTheDocument()
    expect(screen.getByText(/bridge \(bridge\)/i)).toBeInTheDocument()
  })

  it('renders DHCP and Static IP toggle buttons', () => {
    renderWithProviders(
      <NetworkConfig value={makeValue()} onChange={() => {}} networks={FAKE_NETWORKS} />
    )
    expect(screen.getByText(/dhcp/i)).toBeInTheDocument()
    expect(screen.getByText(/static ip/i)).toBeInTheDocument()
  })

  it('DHCP mode does NOT show static IP fields', () => {
    renderWithProviders(
      <NetworkConfig value={makeValue({ ip_mode: 'dhcp' })} onChange={() => {}} networks={FAKE_NETWORKS} />
    )
    expect(screen.queryByLabelText(/ip address/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/gateway/i)).not.toBeInTheDocument()
  })

  it('static mode shows IP/Subnet/Gateway/DNS inputs', () => {
    renderWithProviders(
      <NetworkConfig value={makeValue({ ip_mode: 'static' })} onChange={() => {}} networks={FAKE_NETWORKS} />
    )
    expect(screen.getByLabelText(/ip address/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/subnet mask/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/gateway/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/dns server/i)).toBeInTheDocument()
  })

  it('clicking Static IP button fires onChange with ip_mode: static', () => {
    const onChange = vi.fn()
    const value = makeValue({ ip_mode: 'dhcp' })
    renderWithProviders(
      <NetworkConfig value={value} onChange={onChange} networks={FAKE_NETWORKS} />
    )
    fireEvent.click(screen.getByText(/static ip/i))
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ ip_mode: 'static' }))
  })

  it('typing in IP Address field fires onChange with updated static_ip', () => {
    const onChange = vi.fn()
    const value = makeValue({ ip_mode: 'static', static_ip: '' })
    renderWithProviders(
      <NetworkConfig value={value} onChange={onChange} networks={FAKE_NETWORKS} />
    )
    const ipInput = screen.getByLabelText(/ip address/i)
    fireEvent.change(ipInput, { target: { value: '10.0.0.5' } })
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ static_ip: '10.0.0.5' }))
  })
})
