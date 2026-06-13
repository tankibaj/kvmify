import { useState } from 'react'
import { Input, Select } from '../ui'
import { useNetworks } from '../../api/client'

const IPV4_RE = /^(\d{1,3}\.){3}\d{1,3}$/

export function validateNetworkConfig(value) {
  const errors = {}

  if (!value.network) {
    errors.network = 'Select a network interface'
  }

  if (value.ip_mode === 'static') {
    if (!value.static_ip || !IPV4_RE.test(value.static_ip)) {
      errors.static_ip = 'Enter a valid IPv4 address'
    }
    if (!value.subnet_mask || !IPV4_RE.test(value.subnet_mask)) {
      errors.subnet_mask = 'Enter a valid subnet mask'
    }
    if (!value.gateway || !IPV4_RE.test(value.gateway)) {
      errors.gateway = 'Enter a valid gateway address'
    }
    if (!value.dns || !IPV4_RE.test(value.dns)) {
      errors.dns = 'Enter a valid DNS server address'
    }
  }

  const valid = Object.keys(errors).length === 0
  return { valid, errors }
}

export default function NetworkConfig({ value, onChange, networks: networksProp }) {
  const { data: networksFromHook, isLoading } = useNetworks()
  const networks = networksProp !== undefined ? networksProp : networksFromHook

  const [blurred, setBlurred] = useState({})

  // Auto-select default network on first load
  const hasNetwork = Boolean(value.network)
  if (!hasNetwork && networks && networks.length > 0) {
    const def = networks.find(n => n.is_default) || networks[0]
    if (def) {
      // Schedule outside render
      setTimeout(() => onChange({ ...value, network: def.id }), 0)
    }
  }

  function handleBlur(field) {
    setBlurred(b => ({ ...b, [field]: true }))
  }

  function ipError(field) {
    if (!blurred[field]) return undefined
    const v = value[field]
    if (!v) return undefined
    return IPV4_RE.test(v) ? undefined : 'Invalid IPv4 address'
  }

  if (!networksProp && isLoading) {
    return (
      <div style={{ color: '#64748b', fontSize: 13, padding: '8px 0' }}>
        Loading networks…
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Network Interface */}
      <Select
        label="Network Interface"
        id="network"
        value={value.network}
        onChange={e => onChange({ ...value, network: e.target.value })}
      >
        {!value.network && <option value="">Select network…</option>}
        {(networks || []).map(n => (
          <option key={n.id} value={n.id}>
            {n.label} ({n.mode})
          </option>
        ))}
      </Select>

      {/* IP Assignment toggle */}
      <div>
        <div style={{ fontSize: 12, fontWeight: 500, color: '#94a3b8', marginBottom: 8 }}>
          IP Assignment
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {['dhcp', 'static'].map(mode => {
            const active = value.ip_mode === mode
            return (
              <button
                key={mode}
                type="button"
                onClick={() => onChange({ ...value, ip_mode: mode })}
                style={{
                  padding: '6px 16px',
                  borderRadius: 20,
                  border: `1px solid ${active ? '#6366f1' : '#1e1e2e'}`,
                  background: active ? 'rgba(99,102,241,0.15)' : 'transparent',
                  color: active ? '#6366f1' : '#94a3b8',
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 150ms',
                  outline: 'none',
                }}
              >
                {mode === 'dhcp' ? '◉ DHCP' : '○ Static IP'}
              </button>
            )
          })}
        </div>
      </div>

      {/* Static IP fields */}
      {value.ip_mode === 'static' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Input
            label="IP Address"
            id="static_ip"
            placeholder="192.168.1.100"
            value={value.static_ip}
            onChange={e => onChange({ ...value, static_ip: e.target.value })}
            onBlur={() => handleBlur('static_ip')}
            error={ipError('static_ip')}
          />
          <Input
            label="Subnet Mask"
            id="subnet_mask"
            placeholder="255.255.255.0"
            value={value.subnet_mask}
            onChange={e => onChange({ ...value, subnet_mask: e.target.value })}
            onBlur={() => handleBlur('subnet_mask')}
            error={ipError('subnet_mask')}
          />
          <Input
            label="Gateway"
            id="gateway"
            placeholder="192.168.1.1"
            value={value.gateway}
            onChange={e => onChange({ ...value, gateway: e.target.value })}
            onBlur={() => handleBlur('gateway')}
            error={ipError('gateway')}
          />
          <Input
            label="DNS Server"
            id="dns"
            placeholder="8.8.8.8"
            value={value.dns}
            onChange={e => onChange({ ...value, dns: e.target.value })}
            onBlur={() => handleBlur('dns')}
            error={ipError('dns')}
          />
        </div>
      )}
    </div>
  )
}
