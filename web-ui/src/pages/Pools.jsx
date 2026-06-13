import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import { Button, Card, StatusDot, Modal } from '../components/ui'
import { useCreatePool, useDeletePool, usePatchPool, useSetDefaultPool } from '../api/client'
import CreatePoolModal from '../components/pools/CreatePoolModal'

function formatBytes(bytes) {
  if (bytes == null || bytes === 0) return '—'
  const gib = bytes / (1024 ** 3)
  if (gib >= 1024) return (gib / 1024).toFixed(1) + ' TiB'
  return gib.toFixed(1) + ' GiB'
}

function usageColor(pct) {
  if (pct >= 90) return '#f43f5e'
  if (pct >= 75) return '#f59e0b'
  return '#10b981'
}

function UsageBar({ capacity, allocation }) {
  if (!capacity || capacity === 0) return <span style={{ color: '#475569', fontSize: '12px' }}>—</span>
  const pct = Math.min(100, Math.round((allocation / capacity) * 100))
  const color = usageColor(pct)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '120px' }}>
      <div style={{ flex: 1, height: '4px', background: '#1e1e2e', borderRadius: '2px', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: '2px', transition: 'width 300ms ease' }} />
      </div>
      <span style={{ fontSize: '11px', fontFamily: 'JetBrains Mono, monospace', color, minWidth: '32px', textAlign: 'right' }}>{pct}%</span>
    </div>
  )
}

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

const thStyle = {
  textAlign: 'left',
  padding: '8px 16px',
  fontSize: '11px',
  fontWeight: 600,
  color: '#94a3b8',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  borderBottom: '1px solid #1e1e2e',
}

const tdStyle = {
  padding: '12px 16px',
  fontSize: '13px',
  color: '#e2e8f0',
  verticalAlign: 'middle',
}

export default function Pools() {
  const [createOpen, setCreateOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const poolsQuery = useQuery({
    queryKey: ['pools'],
    queryFn: () => fetch('/api/pools').then(r => r.json()),
    refetchInterval: 10000,
  })
  const pools = poolsQuery.data ?? []

  const createPool = useCreatePool()
  const deletePool = useDeletePool()
  const patchPool = usePatchPool()
  const setDefault = useSetDefaultPool()

  const handleDelete = () => {
    deletePool.mutate({ name: deleteTarget.name }, {
      onSuccess: () => {
        setDeleteOpen(false)
        setDeleteTarget(null)
      },
    })
  }

  return (
    <div>
      <TopBar title="Storage Pools" />
      <div style={{ padding: '24px', maxWidth: '1200px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#e2e8f0' }}>Storage Pools</h2>
            <p style={{ margin: '2px 0 0', fontSize: '12px', color: '#475569' }}>
              {pools.length} pool{pools.length !== 1 ? 's' : ''} configured
            </p>
          </div>
          <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Plus size={14} />
            Create Pool
          </Button>
        </div>

        <Card>
          {poolsQuery.isLoading ? (
            <div style={{ padding: '48px', textAlign: 'center', color: '#94a3b8', fontSize: '14px' }}>
              Loading pools...
            </div>
          ) : poolsQuery.error ? (
            <div style={{ padding: '48px', textAlign: 'center', color: '#f43f5e', fontSize: '14px' }}>
              Failed to load pools: {poolsQuery.error.message}
            </div>
          ) : pools.length === 0 ? (
            <div style={{ padding: '48px', textAlign: 'center', color: '#475569', fontSize: '14px' }}>
              No storage pools configured.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={thStyle}>Name</th>
                  <th style={thStyle}>State</th>
                  <th style={thStyle}>Type</th>
                  <th style={thStyle}>Capacity</th>
                  <th style={thStyle}>Used</th>
                  <th style={thStyle}>Available + Usage</th>
                  <th style={thStyle}>Autostart</th>
                  <th style={thStyle}>Default</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pools.map(pool => (
                  <tr
                    key={pool.name}
                    style={{ borderBottom: '1px solid #1e1e2e' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(30,30,46,0.5)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={tdStyle}>
                      <div>
                        <span style={{ fontWeight: 500, color: '#e2e8f0' }}>{pool.name}</span>
                        {pool.path && (
                          <div style={{ fontSize: '11px', fontFamily: 'JetBrains Mono, monospace', color: '#475569', marginTop: '2px' }}>
                            {pool.path}
                          </div>
                        )}
                      </div>
                    </td>
                    <td style={tdStyle}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <StatusDot status={pool.state === 'active' ? 'running' : 'stopped'} />
                        <span style={{ fontSize: '12px', color: pool.state === 'active' ? '#10b981' : '#94a3b8', textTransform: 'capitalize' }}>
                          {pool.state}
                        </span>
                      </div>
                    </td>
                    <td style={{ ...tdStyle, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: '#94a3b8' }}>
                      {pool.type ?? 'dir'}
                    </td>
                    <td style={{ ...tdStyle, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>
                      {formatBytes(pool.capacity)}
                    </td>
                    <td style={{ ...tdStyle, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>
                      {formatBytes(pool.allocation)}
                    </td>
                    <td style={tdStyle}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: '#94a3b8' }}>
                          {formatBytes(pool.available)}
                        </span>
                        <UsageBar capacity={pool.capacity} allocation={pool.allocation} />
                      </div>
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      <AutostartToggle
                        enabled={pool.autostart}
                        disabled={pool.state === 'inactive'}
                        onClick={() => patchPool.mutate({ name: pool.name, autostart: !pool.autostart })}
                      />
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      {pool.is_default ? (
                        <span style={{ fontSize: '11px', color: '#6366f1', fontWeight: 600, background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.25)', borderRadius: '4px', padding: '2px 6px' }}>
                          default
                        </span>
                      ) : (
                        <span style={{ fontSize: '11px', color: '#475569' }}>—</span>
                      )}
                    </td>
                    <td style={tdStyle}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        {!pool.is_default && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setDefault.mutate({ name: pool.name })}
                          >
                            Set Default
                          </Button>
                        )}
                        {pool.state === 'inactive' ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => patchPool.mutate({ name: pool.name, action: 'start' })}
                          >
                            Start
                          </Button>
                        ) : (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => patchPool.mutate({ name: pool.name, action: 'stop' })}
                          >
                            Stop
                          </Button>
                        )}
                        <Button
                          variant="danger"
                          size="sm"
                          disabled={pool.is_default}
                          title={pool.is_default ? 'Cannot delete the default pool' : undefined}
                          onClick={() => { setDeleteTarget(pool); setDeleteOpen(true) }}
                        >
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <CreatePoolModal
          isOpen={createOpen}
          onClose={() => setCreateOpen(false)}
          onCreate={async (data) => { await createPool.mutateAsync(data) }}
        />

        <Modal
          isOpen={deleteOpen}
          onClose={() => { setDeleteOpen(false); setDeleteTarget(null) }}
          title="Delete Pool"
          footer={
            <>
              <Button variant="ghost" onClick={() => { setDeleteOpen(false); setDeleteTarget(null) }}>Cancel</Button>
              <Button variant="danger" loading={deletePool.isPending} onClick={handleDelete}>Delete</Button>
            </>
          }
        >
          {deleteTarget && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <p style={{ margin: 0, color: '#e2e8f0', fontSize: '14px' }}>
                Are you sure you want to delete pool <strong style={{ color: '#f43f5e' }}>{deleteTarget.name}</strong>? This cannot be undone.
              </p>
              {deleteTarget.volume_count > 0 && (
                <div style={{ background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.2)', borderRadius: '8px', padding: '10px 14px', fontSize: '13px', color: '#f43f5e' }}>
                  Warning: This pool contains {deleteTarget.volume_count} volume{deleteTarget.volume_count > 1 ? 's' : ''}. The backend will reject deletion of non-empty pools unless forced.
                </div>
              )}
            </div>
          )}
        </Modal>
      </div>
    </div>
  )
}
