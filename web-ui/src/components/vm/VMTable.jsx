import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Badge, StatusDot, CopyButton } from '../../components/ui'
import VMActions from './VMActions'

function getOsBadgeStyle(os) {
  if (!os) return {}
  if (os.includes('20.04')) return { color: '#f59e0b' }
  if (os.includes('22.04')) return { color: '#10b981' }
  if (os.includes('24.04')) return { color: '#6366f1' }
  return {}
}

function stateLabel(state) {
  switch (state) {
    case 'running':
      return { label: 'Running', color: '#10b981' }
    case 'stopped':
    case 'shutoff':
      return { label: 'Stopped', color: '#94a3b8' }
    case 'provisioning':
      return { label: 'Provisioning', color: '#f59e0b' }
    default:
      return { label: state, color: '#94a3b8' }
  }
}

const MONO = { fontFamily: "'JetBrains Mono', monospace" }

const thStyle = {
  fontSize: 10,
  textTransform: 'uppercase',
  color: '#475569',
  letterSpacing: '0.07em',
  height: 40,
  textAlign: 'left',
  padding: '0 16px',
  fontWeight: 500,
  borderBottom: '1px solid #1e1e2e',
  whiteSpace: 'nowrap',
}

const tdStyle = {
  padding: '0 16px',
  height: 52,
  verticalAlign: 'middle',
}

export default function VMTable({ vms }) {
  const navigate = useNavigate()
  const [hovered, setHovered] = useState(null)

  if (!vms || vms.length === 0) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '64px 0',
          gap: 12,
          color: '#64748b',
          fontSize: 14,
        }}
      >
        <span>No virtual machines yet.</span>
        <Link
          to="/provision"
          style={{
            color: '#6366f1',
            textDecoration: 'none',
            fontWeight: 500,
            fontSize: 14,
          }}
        >
          Provision your first VM →
        </Link>
      </div>
    )
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table
        style={{
          width: '100%',
          borderCollapse: 'separate',
          borderSpacing: 0,
        }}
      >
        <thead>
          <tr>
            <th style={thStyle}>Name</th>
            <th style={thStyle}>OS</th>
            <th style={thStyle}>Status</th>
            <th style={thStyle}>IP</th>
            <th style={thStyle}>CPU / RAM / Disk</th>
            <th style={thStyle}>Uptime</th>
            <th style={thStyle}></th>
          </tr>
        </thead>
        <tbody>
          {vms.map((vm) => {
            const { label, color } = stateLabel(vm.state)
            const ramLabel = vm.ram_mb ? (vm.ram_mb / 1024).toFixed(1) + 'GB' : '—'
            const diskLabel = vm.disk_gb ? vm.disk_gb + 'GB' : '—'
            const cpuLabel = vm.vcpus ?? '—'
            const isHovered = hovered === vm.name

            return (
              <tr
                key={vm.name}
                style={{
                  background: isHovered ? 'rgba(255,255,255,0.02)' : 'transparent',
                  transition: 'background 150ms',
                  borderBottom: '1px solid rgba(30,30,46,0.6)',
                }}
                onMouseEnter={() => setHovered(vm.name)}
                onMouseLeave={() => setHovered(null)}
              >
                {/* Name */}
                <td
                  style={{ ...tdStyle, cursor: 'pointer' }}
                  onClick={() => navigate(`/vms/${vm.name}`)}
                >
                  <span
                    style={{
                      fontWeight: 600,
                      fontSize: 13,
                      color: '#e2e8f0',
                    }}
                  >
                    {vm.name}
                  </span>
                </td>

                {/* OS */}
                <td style={tdStyle}>
                  {vm.os ? (
                    <Badge variant="default">
                      <span style={getOsBadgeStyle(vm.os)}>{vm.os}</span>
                    </Badge>
                  ) : (
                    <span style={{ color: '#64748b', fontSize: 13 }}>—</span>
                  )}
                </td>

                {/* Status */}
                <td style={tdStyle}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                    <StatusDot status={vm.state} />
                    <span style={{ fontSize: 13, color }}>{label}</span>
                  </div>
                </td>

                {/* IP */}
                <td style={{ ...tdStyle, ...MONO, fontSize: 12 }}>
                  {vm.ip ? (
                    <CopyButton text={vm.ip} label={vm.ip} />
                  ) : (
                    <span style={{ color: '#64748b' }}>—</span>
                  )}
                </td>

                {/* CPU / RAM / Disk */}
                <td
                  style={{
                    ...tdStyle,
                    ...MONO,
                    fontSize: 12,
                    color: '#94a3b8',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {cpuLabel} vCPU · {ramLabel} · {diskLabel}
                </td>

                {/* Uptime */}
                <td style={{ ...tdStyle, fontSize: 12, color: '#64748b', whiteSpace: 'nowrap' }}>
                  {vm.uptime ?? '—'}
                </td>

                {/* Actions */}
                <td style={{ ...tdStyle, textAlign: 'right' }}>
                  <VMActions vm={vm} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
