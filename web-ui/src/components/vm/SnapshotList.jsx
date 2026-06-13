import { useState } from 'react'
import { useVMSnapshots, useCreateSnapshot, useRestoreSnapshot, useDeleteSnapshot } from '../../api/client'
import { Button, Badge, Modal } from '../ui'
import { Camera, RotateCcw, Trash2 } from 'lucide-react'

function formatDate(iso) {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

function padTwo(n) {
  return String(n).padStart(2, '0')
}

function defaultSnapName(vmName) {
  const now = new Date()
  const YYYYMMDD = `${now.getFullYear()}${padTwo(now.getMonth() + 1)}${padTwo(now.getDate())}`
  const HHmm = `${padTwo(now.getHours())}${padTwo(now.getMinutes())}`
  return `${vmName}-${YYYYMMDD}-${HHmm}`
}

export default function SnapshotList({ vmName }) {
  const { data: snapshots, isLoading } = useVMSnapshots(vmName)

  const createSnap = useCreateSnapshot()
  const restoreSnap = useRestoreSnapshot()
  const deleteSnap = useDeleteSnapshot()

  // Take snapshot modal
  const [takeOpen, setTakeOpen] = useState(false)
  const [snapName, setSnapName] = useState('')
  const [snapDesc, setSnapDesc] = useState('')

  // Restore confirm modal
  const [restoreTarget, setRestoreTarget] = useState(null)

  // Delete confirm modal
  const [deleteTarget, setDeleteTarget] = useState(null)

  function openTake() {
    setSnapName(defaultSnapName(vmName))
    setSnapDesc('')
    setTakeOpen(true)
  }

  function handleTakeConfirm() {
    createSnap.mutate(
      { name: vmName, snapshot_name: snapName, description: snapDesc || undefined },
      { onSuccess: () => setTakeOpen(false) }
    )
  }

  function handleRestoreConfirm() {
    if (!restoreTarget) return
    restoreSnap.mutate(
      { name: vmName, snap: restoreTarget },
      { onSuccess: () => setRestoreTarget(null) }
    )
  }

  function handleDeleteConfirm() {
    if (!deleteTarget) return
    deleteSnap.mutate(
      { name: vmName, snap: deleteTarget },
      { onSuccess: () => setDeleteTarget(null) }
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button variant="primary" size="sm" onClick={openTake}>
          <Camera size={13} />
          Take Snapshot
        </Button>
      </div>

      {/* List */}
      {isLoading ? (
        <div
          style={{
            padding: '40px 0',
            textAlign: 'center',
            color: '#475569',
            fontSize: '13px',
          }}
        >
          Loading snapshots…
        </div>
      ) : !snapshots?.length ? (
        <div
          style={{
            padding: '48px 0',
            textAlign: 'center',
            color: '#475569',
            fontSize: '13px',
          }}
        >
          <Camera size={32} style={{ opacity: 0.3, marginBottom: '12px' }} />
          <div>No snapshots yet.</div>
        </div>
      ) : (
        <div
          style={{
            border: '1px solid #1e1e2e',
            borderRadius: '10px',
            overflow: 'hidden',
          }}
        >
          {snapshots.map((snap, i) => (
            <div
              key={snap.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '14px 16px',
                background: i % 2 === 0 ? '#111118' : '#0d0d14',
                borderBottom:
                  i < snapshots.length - 1 ? '1px solid #1e1e2e' : 'none',
              }}
            >
              {/* Name + description */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    flexWrap: 'wrap',
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: '13px',
                      color: '#e2e8f0',
                      fontWeight: 500,
                    }}
                  >
                    {snap.name}
                  </span>
                  {snap.is_current && (
                    <Badge variant="running">current</Badge>
                  )}
                  {snap.state && (
                    <Badge variant="default">{snap.state}</Badge>
                  )}
                </div>
                {snap.description && (
                  <div
                    style={{
                      fontSize: '12px',
                      color: '#64748b',
                      marginTop: '2px',
                    }}
                  >
                    {snap.description}
                  </div>
                )}
              </div>

              {/* Date */}
              <div
                style={{
                  fontSize: '12px',
                  color: '#64748b',
                  whiteSpace: 'nowrap',
                }}
              >
                {formatDate(snap.created)}
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setRestoreTarget(snap.name)}
                  style={{ color: '#6366f1' }}
                >
                  <RotateCcw size={12} />
                  Restore
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setDeleteTarget(snap.name)}
                  style={{ color: '#f43f5e' }}
                >
                  <Trash2 size={12} />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Take Snapshot Modal */}
      <Modal
        isOpen={takeOpen}
        onClose={() => setTakeOpen(false)}
        title="Take Snapshot"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setTakeOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              loading={createSnap.isPending}
              disabled={!snapName.trim()}
              onClick={handleTakeConfirm}
            >
              <Camera size={13} />
              Take Snapshot
            </Button>
          </>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label
              style={{ fontSize: '12px', fontWeight: 500, color: '#94a3b8' }}
            >
              Snapshot Name
            </label>
            <input
              value={snapName}
              onChange={(e) => setSnapName(e.target.value)}
              style={{
                background: '#0a0a0f',
                border: '1px solid #1e1e2e',
                borderRadius: '8px',
                padding: '8px 12px',
                color: '#e2e8f0',
                fontSize: '13px',
                outline: 'none',
                fontFamily: 'JetBrains Mono, monospace',
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = '#6366f1')}
              onBlur={(e) => (e.currentTarget.style.borderColor = '#1e1e2e')}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label
              style={{ fontSize: '12px', fontWeight: 500, color: '#94a3b8' }}
            >
              Description{' '}
              <span style={{ color: '#475569', fontWeight: 400 }}>(optional)</span>
            </label>
            <input
              value={snapDesc}
              onChange={(e) => setSnapDesc(e.target.value)}
              placeholder="e.g. Before nginx upgrade"
              style={{
                background: '#0a0a0f',
                border: '1px solid #1e1e2e',
                borderRadius: '8px',
                padding: '8px 12px',
                color: '#e2e8f0',
                fontSize: '13px',
                outline: 'none',
                fontFamily: 'inherit',
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = '#6366f1')}
              onBlur={(e) => (e.currentTarget.style.borderColor = '#1e1e2e')}
            />
          </div>
        </div>
      </Modal>

      {/* Restore Confirm Modal */}
      <Modal
        isOpen={!!restoreTarget}
        onClose={() => setRestoreTarget(null)}
        title="Restore Snapshot"
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setRestoreTarget(null)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              loading={restoreSnap.isPending}
              onClick={handleRestoreConfirm}
            >
              <RotateCcw size={13} />
              Restore
            </Button>
          </>
        }
      >
        <p style={{ margin: 0, fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>
          Restore VM <strong style={{ color: '#e2e8f0' }}>{vmName}</strong> to snapshot{' '}
          <strong
            style={{
              color: '#6366f1',
              fontFamily: 'JetBrains Mono, monospace',
            }}
          >
            {restoreTarget}
          </strong>
          ? The current VM state will be discarded.
        </p>
      </Modal>

      {/* Delete Confirm Modal */}
      <Modal
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete Snapshot"
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setDeleteTarget(null)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={deleteSnap.isPending}
              onClick={handleDeleteConfirm}
            >
              <Trash2 size={13} />
              Delete
            </Button>
          </>
        }
      >
        <p style={{ margin: 0, fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>
          Permanently delete snapshot{' '}
          <strong
            style={{
              color: '#f43f5e',
              fontFamily: 'JetBrains Mono, monospace',
            }}
          >
            {deleteTarget}
          </strong>
          ? This cannot be undone.
        </p>
      </Modal>
    </div>
  )
}
