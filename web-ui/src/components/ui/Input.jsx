import { useState } from 'react'

export function Input({ label, error, id, className, ...props }) {
  const [focused, setFocused] = useState(false)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      {label && (
        <label
          htmlFor={id}
          style={{ fontSize: '12px', fontWeight: 500, color: '#94a3b8' }}
        >
          {label}
        </label>
      )}
      <input
        id={id}
        className={className}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          background: '#0a0a0f',
          border: `1px solid ${error ? '#f43f5e' : focused ? '#6366f1' : '#1e1e2e'}`,
          borderRadius: '8px',
          padding: '8px 12px',
          color: '#e2e8f0',
          fontSize: '13px',
          outline: 'none',
          width: '100%',
          transition: 'border-color 150ms ease',
          boxShadow: focused && !error ? '0 0 0 2px rgba(99,102,241,0.15)' : 'none',
          fontFamily: 'inherit',
        }}
        {...props}
      />
      {error && (
        <span style={{ fontSize: '11px', color: '#f43f5e' }}>{error}</span>
      )}
    </div>
  )
}

export function Select({ label, error, id, children, className, ...props }) {
  const [focused, setFocused] = useState(false)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      {label && (
        <label
          htmlFor={id}
          style={{ fontSize: '12px', fontWeight: 500, color: '#94a3b8' }}
        >
          {label}
        </label>
      )}
      <select
        id={id}
        className={className}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          background: '#0a0a0f',
          border: `1px solid ${error ? '#f43f5e' : focused ? '#6366f1' : '#1e1e2e'}`,
          borderRadius: '8px',
          padding: '8px 12px',
          color: '#e2e8f0',
          fontSize: '13px',
          outline: 'none',
          width: '100%',
          transition: 'border-color 150ms ease',
          boxShadow: focused && !error ? '0 0 0 2px rgba(99,102,241,0.15)' : 'none',
          fontFamily: 'inherit',
          cursor: 'pointer',
        }}
        {...props}
      >
        {children}
      </select>
      {error && (
        <span style={{ fontSize: '11px', color: '#f43f5e' }}>{error}</span>
      )}
    </div>
  )
}

export default Input
