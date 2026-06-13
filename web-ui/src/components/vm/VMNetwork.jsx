import { useState } from 'react'
import NetworkConfig, { validateNetworkConfig } from '../provision/NetworkConfig'
import { useUpdateVMNetwork } from '../../api/client'
import { Button } from '../ui'
import { AlertTriangle, Save } from 'lucide-react'

function InfoRow({ label, value, mono }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '10px 0',
        borderBottom: '1px solid #1e1e2e',
      }}
    >
      <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 500 }}>
        {label}
      </span>
      <span
        style={{
          fontSize: '13px',
          color: '#e2e8f0',
          fontFamily: mono ? 'JetBrains Mono, monospace' : 'inherit',
        }}
      >
        {value ?? '—'}
      </span>
    </div>
  )
}

export default function VMNetwork({ vm }) {
  const updateNetwork = useUpdateVMNetwork()

  const [netConfig, setNetConfig] = useState({
    network: vm?.network ?? '',
    ip_mode: vm?.ip_mode ?? 'dhcp',
    static_ip: '',
    subnet_mask: '',
    gateway: '',
    dns: '',
  })
  const [errors, setErrors] = useState({})

  function handleApply() {
    const result = validateNetworkConfig(netConfig)
    if (!result.valid) {
      setErrors(result.errors)
      return
    }
    setErrors({})
    updateNetwork.mutate({ name: vm.name, ...netConfig })
  }

  const modeLabel = {
    bridge: 'Bridge',
    nat: 'NAT',
    macvtap: 'Macvtap',
  }[vm?.network?.toLowerCase?.()] ?? vm?.network ?? '—'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Current config read-out */}
      <div
        style={{
          background: '#0a0a0f',
          border: '1px solid #1e1e2e',
          borderRadius: '10px',
          padding: '16px',
        }}
      >
        <div
          style={{
            fontSize: '11px',
            fontWeight: 600,
            color: '#475569',
            textTransform: 'uppercase',
            letterSpacing: '0.07em',
            marginBottom: '4px',
          }}
        >
          Current Configuration
        </div>
        <InfoRow label="Interface" value={vm?.network} />
        <InfoRow label="Mode" value={modeLabel} />
        <InfoRow label="IP Assignment" value={vm?.ip_mode === 'static' ? 'Static' : 'DHCP'} />
        <InfoRow label="IP Address" value={vm?.ip} mono />
        <div style={{ paddingTop: '10px' }}>
          <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 500 }}>MAC Address</span>
          <div
            style={{
              marginTop: '4px',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '13px',
              color: '#e2e8f0',
            }}
          >
            {vm?.mac ?? '—'}
          </div>
        </div>
      </div>

      {/* Amber warning */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '10px',
          background: 'rgba(245,158,11,0.08)',
          border: '1px solid rgba(245,158,11,0.25)',
          borderRadius: '8px',
          padding: '12px 14px',
        }}
      >
        <AlertTriangle size={14} style={{ color: '#f59e0b', flexShrink: 0, marginTop: '1px' }} />
        <span style={{ fontSize: '12px', color: '#f59e0b', lineHeight: 1.5 }}>
          Network changes require a VM restart to take effect.
        </span>
      </div>

      {/* NetworkConfig form */}
      <NetworkConfig value={netConfig} onChange={setNetConfig} />

      {/* Validation errors summary */}
      {Object.keys(errors).length > 0 && (
        <div
          style={{
            background: 'rgba(244,63,94,0.08)',
            border: '1px solid rgba(244,63,94,0.25)',
            borderRadius: '8px',
            padding: '10px 14px',
          }}
        >
          {Object.values(errors).map((e, i) => (
            <div key={i} style={{ fontSize: '12px', color: '#f43f5e' }}>
              {e}
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="primary"
          size="sm"
          loading={updateNetwork.isPending}
          onClick={handleApply}
        >
          <Save size={13} />
          Apply Changes
        </Button>
      </div>
    </div>
  )
}
