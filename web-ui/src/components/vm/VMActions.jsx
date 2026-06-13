import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MoreHorizontal,
  Play,
  Square,
  RefreshCw,
  Terminal,
  Camera,
  Maximize2,
  Trash2,
} from 'lucide-react'
import { Button, Modal } from '../../components/ui'
import {
  useStartVM,
  useStopVM,
  useRestartVM,
  useDeleteVM,
} from '../../api/client'

export default function VMActions({ vm }) {
  const [open, setOpen] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const wrapperRef = useRef(null)
  const navigate = useNavigate()

  const startVM = useStartVM()
  const stopVM = useStopVM()
  const restartVM = useRestartVM()
  const deleteVM = useDeleteVM()

  const isStopped = vm.state === 'shutoff' || vm.state === 'stopped'
  const isRunning = vm.state === 'running'

  // Close dropdown on outside click
  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  // Close modal on successful delete
  useEffect(() => {
    if (deleteVM.isSuccess) {
      setShowDeleteModal(false)
    }
  }, [deleteVM.isSuccess])

  function handleAction(fn) {
    fn()
    setOpen(false)
  }

  const menuItemBase = {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '7px 12px',
    borderRadius: 6,
    fontSize: 13,
    cursor: 'pointer',
    transition: 'background 150ms',
    border: 'none',
    background: 'transparent',
    width: '100%',
    textAlign: 'left',
    color: '#94a3b8',
  }

  const disabledItemStyle = {
    ...menuItemBase,
    opacity: 0.4,
    cursor: 'not-allowed',
  }

  const separatorStyle = {
    height: 1,
    background: '#1e1e2e',
    margin: '4px 0',
  }

  return (
    <div ref={wrapperRef} style={{ position: 'relative', display: 'inline-block' }}>
      <Button
        variant="ghost"
        size="sm"
        onClick={(e) => {
          e.stopPropagation()
          setOpen((v) => !v)
        }}
      >
        <MoreHorizontal size={14} />
      </Button>

      {open && (
        <div
          style={{
            position: 'absolute',
            right: 0,
            top: '100%',
            marginTop: 4,
            zIndex: 200,
            background: '#111118',
            border: '1px solid #1e1e2e',
            borderRadius: 8,
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            minWidth: 160,
            padding: 4,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Start */}
          {isRunning ? (
            <div style={disabledItemStyle}>
              <Play size={13} color="#10b981" />
              <span>Start</span>
            </div>
          ) : (
            <button
              style={menuItemBase}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              onClick={() => handleAction(() => startVM.mutate({ name: vm.name }))}
            >
              <Play size={13} color="#10b981" />
              <span style={{ color: '#10b981' }}>Start</span>
            </button>
          )}

          {/* Stop */}
          {isStopped ? (
            <div style={disabledItemStyle}>
              <Square size={13} />
              <span>Stop</span>
            </div>
          ) : (
            <button
              style={menuItemBase}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              onClick={() => handleAction(() => stopVM.mutate({ name: vm.name }))}
            >
              <Square size={13} />
              <span>Stop</span>
            </button>
          )}

          {/* Restart */}
          {!isRunning ? (
            <div style={disabledItemStyle}>
              <RefreshCw size={13} />
              <span>Restart</span>
            </div>
          ) : (
            <button
              style={menuItemBase}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              onClick={() => handleAction(() => restartVM.mutate({ name: vm.name }))}
            >
              <RefreshCw size={13} />
              <span>Restart</span>
            </button>
          )}

          <div style={separatorStyle} />

          {/* Console */}
          <button
            style={menuItemBase}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            onClick={() => handleAction(() => navigate(`/vms/${vm.name}?tab=console`))}
          >
            <Terminal size={13} />
            <span>Console</span>
          </button>

          {/* Snapshots */}
          <button
            style={menuItemBase}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            onClick={() => handleAction(() => navigate(`/vms/${vm.name}?tab=snapshots`))}
          >
            <Camera size={13} />
            <span>Snapshots</span>
          </button>

          {/* Resize */}
          <button
            style={menuItemBase}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            onClick={() => handleAction(() => navigate(`/vms/${vm.name}?tab=resize`))}
          >
            <Maximize2 size={13} />
            <span>Resize</span>
          </button>

          <div style={separatorStyle} />

          {/* Delete */}
          <button
            style={{ ...menuItemBase, color: '#f43f5e' }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(244,63,94,0.1)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            onClick={() => {
              setOpen(false)
              setShowDeleteModal(true)
            }}
          >
            <Trash2 size={13} color="#f43f5e" />
            <span>Delete</span>
          </button>
        </div>
      )}

      {/* Delete confirmation modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete VM"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={deleteVM.isPending}
              onClick={() => deleteVM.mutate({ name: vm.name })}
            >
              Delete
            </Button>
          </>
        }
      >
        <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6, margin: 0 }}>
          Are you sure you want to delete <strong style={{ color: '#e2e8f0' }}>{vm.name}</strong>?
          This action cannot be undone.
        </p>
      </Modal>
    </div>
  )
}
