import { Loader2 } from 'lucide-react'

const variants = {
  primary: {
    background: '#6366f1',
    color: '#ffffff',
    border: '1px solid #6366f1',
    hoverBg: '#5558e8',
    hoverShadow: '0 0 12px rgba(99,102,241,0.3)',
  },
  ghost: {
    background: 'transparent',
    color: '#94a3b8',
    border: '1px solid #1e1e2e',
    hoverBg: '#1e1e2e',
    hoverShadow: 'none',
  },
  danger: {
    background: '#f43f5e',
    color: '#ffffff',
    border: '1px solid #f43f5e',
    hoverBg: '#e11d48',
    hoverShadow: '0 0 12px rgba(244,63,94,0.3)',
  },
  success: {
    background: '#10b981',
    color: '#ffffff',
    border: '1px solid #10b981',
    hoverBg: '#059669',
    hoverShadow: '0 0 12px rgba(16,185,129,0.3)',
  },
}

const sizes = {
  sm: { padding: '4px 12px', fontSize: '12px', height: '28px' },
  md: { padding: '6px 16px', fontSize: '13px', height: '36px' },
  lg: { padding: '10px 24px', fontSize: '15px', height: '44px' },
}

export default function Button({
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  onClick,
  type = 'button',
  className,
  children,
  style: styleProp,
}) {
  const v = variants[variant] || variants.primary
  const s = sizes[size] || sizes.md

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '6px',
        background: v.background,
        color: v.color,
        border: v.border,
        borderRadius: '8px',
        padding: s.padding,
        fontSize: s.fontSize,
        height: s.height,
        fontWeight: 500,
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled || loading ? 0.5 : 1,
        transition: 'all 150ms ease',
        fontFamily: 'inherit',
        whiteSpace: 'nowrap',
        ...styleProp,
      }}
      onMouseEnter={e => {
        if (!disabled && !loading) {
          e.currentTarget.style.background = v.hoverBg
          if (v.hoverShadow !== 'none') e.currentTarget.style.boxShadow = v.hoverShadow
        }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = v.background
        e.currentTarget.style.boxShadow = 'none'
      }}
    >
      {loading && <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />}
      {children}
    </button>
  )
}
