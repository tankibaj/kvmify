export default function Card({ title, children, className, elevated = false, style: styleProp }) {
  return (
    <div
      className={className}
      style={{
        background: '#111118',
        border: '1px solid #1e1e2e',
        borderRadius: '12px',
        overflow: 'hidden',
        boxShadow: elevated ? '0 4px 24px rgba(0,0,0,0.3)' : 'none',
        ...styleProp,
      }}
    >
      {title && (
        <div
          style={{
            padding: '14px 20px',
            borderBottom: '1px solid #1e1e2e',
            fontSize: '13px',
            fontWeight: 600,
            color: '#94a3b8',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          {title}
        </div>
      )}
      <div style={{ padding: title ? '20px' : '20px' }}>{children}</div>
    </div>
  )
}
