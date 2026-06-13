import { CheckCircle2, XCircle, Info, AlertTriangle, X } from 'lucide-react'
import { useNotify } from '../../contexts/NotificationContext'

const variantConfig = {
  success: {
    icon: CheckCircle2,
    borderColor: '#10b981',
    iconColor: '#10b981',
  },
  error: {
    icon: XCircle,
    borderColor: '#f43f5e',
    iconColor: '#f43f5e',
  },
  info: {
    icon: Info,
    borderColor: '#64748b',
    iconColor: '#94a3b8',
  },
  warning: {
    icon: AlertTriangle,
    borderColor: '#f59e0b',
    iconColor: '#f59e0b',
  },
}

function Toast({ toast, onDismiss }) {
  const config = variantConfig[toast.variant] || variantConfig.info
  const Icon = config.icon

  return (
    <div
      style={{
        background: '#111118',
        border: '1px solid #1e1e2e',
        borderLeft: `3px solid ${config.borderColor}`,
        borderRadius: '8px',
        padding: '12px 16px',
        width: '320px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '10px',
        boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
        animation: 'slideInRight 150ms ease',
      }}
    >
      <Icon size={16} style={{ color: config.iconColor, flexShrink: 0, marginTop: '2px' }} />
      <span style={{ color: '#e2e8f0', fontSize: '13px', lineHeight: '1.5', flex: 1 }}>
        {toast.message}
      </span>
      <button
        onClick={() => onDismiss(toast.id)}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: '#64748b',
          padding: '0',
          display: 'flex',
          alignItems: 'center',
          transition: 'color 150ms ease',
        }}
        onMouseEnter={e => e.currentTarget.style.color = '#e2e8f0'}
        onMouseLeave={e => e.currentTarget.style.color = '#64748b'}
      >
        <X size={14} />
      </button>
    </div>
  )
}

export default function NotificationToast() {
  const { toasts, dismiss } = useNotify()

  if (toasts.length === 0) return null

  return (
    <>
      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
      <div
        style={{
          position: 'fixed',
          top: '16px',
          right: '16px',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        {toasts.map(toast => (
          <Toast key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </div>
    </>
  )
}
