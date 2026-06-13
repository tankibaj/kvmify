export default function Slider({ min, max, step = 1, value, onChange, label, unit }) {
  const pct = ((value - min) / (max - min)) * 100

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {label && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', fontWeight: 500, color: '#94a3b8' }}>{label}</span>
          <span style={{ fontSize: '13px', fontWeight: 600, color: '#6366f1', fontFamily: 'JetBrains Mono, monospace' }}>
            {value}{unit && ` ${unit}`}
          </span>
        </div>
      )}
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{
          appearance: 'none',
          width: '100%',
          height: '4px',
          borderRadius: '2px',
          background: `linear-gradient(to right, #6366f1 ${pct}%, #1e1e2e ${pct}%)`,
          outline: 'none',
          cursor: 'pointer',
        }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '10px', color: '#475569' }}>{min}{unit && ` ${unit}`}</span>
        <span style={{ fontSize: '10px', color: '#475569' }}>{max}{unit && ` ${unit}`}</span>
      </div>
    </div>
  )
}
