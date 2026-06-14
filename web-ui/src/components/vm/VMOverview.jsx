import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStartVM, useStopVM, useRestartVM, useDeleteVM, usePatchVM } from '../../api/client'
import { Card, Button, Badge, StatusDot, CopyButton, Modal } from '../ui'
import VMStats from './VMStats'
import { formatUptime } from './VMTable'
import { Play, Square, RotateCcw, Trash2 } from 'lucide-react'

function AutostartToggle({ enabled, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={enabled ? 'Autostart enabled — click to disable' : 'Autostart disabled — click to enable'}
      style={{
        width: '32px', height: '18px',
        background: enabled ? 'rgba(99,102,241,0.3)' : '#1e1e2e',
        border: `1px solid ${enabled ? '#6366f1' : '#2e2e4e'}`,
        borderRadius: '9px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        position: 'relative',
        transition: 'all 150ms ease',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <span style={{
        position: 'absolute',
        top: '2px',
        left: enabled ? '14px' : '2px',
        width: '12px', height: '12px',
        background: enabled ? '#6366f1' : '#475569',
        borderRadius: '50%',
        transition: 'left 150ms ease',
      }} />
    </button>
  )
}

function MetaRow({ label, children }) {
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
      <div style={{ fontSize: '13px', color: '#e2e8f0' }}>{children}</div>
    </div>
  )
}

function SectionLabel({ children }) {
  return (
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
      {children}
    </div>
  )
}

export default function VMOverview({ vm }) {
  const navigate = useNavigate()
  const startVM = useStartVM()
  const stopVM = useStopVM()
  const restartVM = useRestartVM()
  const deleteVM = useDeleteVM()
  const patchVM = usePatchVM()

  const [showDeleteModal, setShowDeleteModal] = useState(false)

  const isRunning = vm?.state === 'running'
  const isStopped = vm?.state === 'shutoff' || vm?.state === 'stopped'
  const name = vm?.name ?? ''

  function handleDelete() {
    deleteVM.mutate(
      { name },
      {
        onSuccess: () => {
          setShowDeleteModal(false)
          navigate('/')
        },
      }
    )
  }

  const networkMode = (() => {
    const net = vm?.network?.toLowerCase?.() ?? ''
    if (net.includes('bridge') || net.startsWith('br')) return 'Bridge'
    if (net === 'nat' || net === 'default') return 'NAT'
    if (net.includes('macvtap')) return 'Macvtap'
    return vm?.network ?? '—'
  })()

  const sshString = vm?.ip ? `ssh ubuntu@${vm.ip}` : null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
          gap: '16px',
        }}
      >
        {/* Metadata card */}
        <Card title="Identity">
          <MetaRow label="Name">
            <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{name}</span>
          </MetaRow>
          <MetaRow label="OS">
            {vm?.os_variant ? (
              <Badge variant="default">{vm.os_variant}</Badge>
            ) : (
              <span style={{ color: '#475569' }}>—</span>
            )}
          </MetaRow>
          <MetaRow label="Status">
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <StatusDot status={vm?.state ?? 'stopped'} />
              <span style={{ textTransform: 'capitalize' }}>{vm?.state ?? '—'}</span>
            </div>
          </MetaRow>
          <MetaRow label="Uptime">
            <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>
              {isRunning ? formatUptime(vm?.uptime) : '—'}
            </span>
          </MetaRow>
          <MetaRow label="IP Address">
            {vm?.ip ? (
              <CopyButton text={vm.ip} label={vm.ip} />
            ) : (
              <span style={{ color: '#475569' }}>—</span>
            )}
          </MetaRow>
          <MetaRow label="Autostart">
            <AutostartToggle
              enabled={!!vm?.autostart}
              disabled={patchVM.isPending || !name}
              onClick={() => patchVM.mutate({ name, autostart: !vm?.autostart })}
            />
          </MetaRow>
        </Card>

        {/* Resources */}
        <Card title="Resources">
          <div
            style={{ display: 'flex', gap: '16px', justifyContent: 'space-around' }}
          >
            {[
              {
                label: 'vCPUs',
                value: vm?.vcpus ?? '—',
                unit: vm?.vcpus ? (vm.vcpus > 1 ? 'cores' : 'core') : '',
              },
              {
                label: 'RAM',
                value:
                  vm?.ram_mb != null
                    ? (vm.ram_mb / 1024).toFixed(1)
                    : '—',
                unit: 'GB',
              },
              {
                label: 'Disk',
                value: vm?.disk_gb ?? '—',
                unit: vm?.disk_gb ? 'GB' : '',
              },
            ].map(({ label, value, unit }) => (
              <div
                key={label}
                style={{ textAlign: 'center', flex: 1 }}
              >
                <div
                  style={{
                    fontSize: '28px',
                    fontWeight: 700,
                    fontFamily: 'JetBrains Mono, monospace',
                    color: '#6366f1',
                    lineHeight: 1.2,
                  }}
                >
                  {value}
                </div>
                <div
                  style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}
                >
                  {label}
                  {unit ? ` (${unit})` : ''}
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Network */}
        <Card title="Network">
          <MetaRow label="Interface">
            <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>
              {vm?.network ?? '—'}
            </span>
          </MetaRow>
          <MetaRow label="Mode">
            <Badge variant="default">{networkMode}</Badge>
          </MetaRow>
          <MetaRow label="IP Assignment">
            <Badge variant={vm?.ip_mode === 'static' ? 'default' : 'running'}>
              {vm?.ip_mode === 'static' ? 'Static' : 'DHCP'}
            </Badge>
          </MetaRow>
          <div style={{ paddingTop: '10px' }}>
            <SectionLabel>MAC Address</SectionLabel>
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '13px',
                color: '#e2e8f0',
              }}
            >
              {vm?.mac ?? '—'}
            </span>
          </div>
        </Card>

        {/* SSH */}
        <Card title="SSH Access">
          {sshString ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <SectionLabel>Connect</SectionLabel>
              <CopyButton text={sshString} label={sshString} />
            </div>
          ) : (
            <div
              style={{
                fontSize: '13px',
                color: '#475569',
                padding: '8px 0',
              }}
            >
              No IP address assigned yet.
            </div>
          )}
        </Card>
      </div>

      {/* Live Sparklines */}
      {isRunning && (
        <Card title="Live Metrics">
          <VMStats vmName={name} />
        </Card>
      )}

      {/* Quick Actions */}
      <Card title="Actions">
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <Button
            variant="success"
            size="sm"
            disabled={isRunning || startVM.isPending}
            loading={startVM.isPending}
            onClick={() => startVM.mutate({ name })}
          >
            <Play size={13} />
            Start
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={isStopped || stopVM.isPending}
            loading={stopVM.isPending}
            onClick={() => stopVM.mutate({ name })}
          >
            <Square size={13} />
            Stop
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={isStopped || restartVM.isPending}
            loading={restartVM.isPending}
            onClick={() => restartVM.mutate({ name })}
          >
            <RotateCcw size={13} />
            Restart
          </Button>
          <Button
            variant="danger"
            size="sm"
            loading={deleteVM.isPending}
            onClick={() => setShowDeleteModal(true)}
            style={{ marginLeft: 'auto' }}
          >
            <Trash2 size={13} />
            Delete VM
          </Button>
        </div>
      </Card>

      {/* Delete confirm modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Virtual Machine"
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowDeleteModal(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={deleteVM.isPending}
              onClick={handleDelete}
            >
              <Trash2 size={13} />
              Delete
            </Button>
          </>
        }
      >
        <p
          style={{
            margin: 0,
            fontSize: '13px',
            color: '#94a3b8',
            lineHeight: 1.6,
          }}
        >
          Permanently delete VM{' '}
          <strong
            style={{
              color: '#f43f5e',
              fontFamily: 'JetBrains Mono, monospace',
            }}
          >
            {name}
          </strong>
          ? This will destroy all data and cannot be undone.
        </p>
      </Modal>
    </div>
  )
}
