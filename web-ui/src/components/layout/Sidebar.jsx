import { NavLink } from 'react-router-dom'
import { LayoutDashboard, HardDrive, Database, Plus } from 'lucide-react'
import { useHostStats } from '../../api/client'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/images', icon: HardDrive, label: 'Images' },
  { to: '/pools', icon: Database, label: 'Pools' },
  { to: '/provision', icon: Plus, label: 'Provision' },
]

function MiniProgress({ value, max, color = '#6366f1' }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0
  return (
    <div style={{ height: '3px', background: '#1e1e2e', borderRadius: '2px', overflow: 'hidden' }}>
      <div style={{ width: `${pct}%`, height: '100%', background: color, transition: 'width 300ms ease', borderRadius: '2px' }} />
    </div>
  )
}

export default function Sidebar() {
  const { data: stats, isLoading } = useHostStats()

  return (
    <div
      style={{
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
        width: '240px',
        background: '#111118',
        borderRight: '1px solid #1e1e2e',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 100,
      }}
    >
      {/* Logo */}
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid #1e1e2e' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '28px',
            height: '28px',
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            borderRadius: '7px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '13px',
            fontWeight: 700,
            color: '#fff',
            flexShrink: 0,
          }}>K</div>
          <span style={{ fontSize: '16px', fontWeight: 700, color: '#e2e8f0', letterSpacing: '-0.01em' }}>
            KVMify
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '8px' }}>
        {navItems.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '8px 12px',
              borderRadius: '8px',
              marginBottom: '2px',
              textDecoration: 'none',
              fontSize: '13px',
              fontWeight: 500,
              color: isActive ? '#6366f1' : '#94a3b8',
              background: isActive ? 'rgba(99,102,241,0.1)' : 'transparent',
              borderLeft: isActive ? '2px solid #6366f1' : '2px solid transparent',
              transition: 'all 150ms ease',
            })}
            onMouseEnter={e => {
              if (!e.currentTarget.classList.contains('active')) {
                e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
                e.currentTarget.style.color = '#e2e8f0'
              }
            }}
            onMouseLeave={e => {
              const isActive = e.currentTarget.getAttribute('aria-current') === 'page'
              if (!isActive) {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.color = '#94a3b8'
              }
            }}
          >
            <Icon size={15} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Host stats */}
      <div style={{ padding: '16px 20px', borderTop: '1px solid #1e1e2e' }}>
        <div style={{ fontSize: '10px', fontWeight: 600, color: '#475569', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '12px' }}>
          HOST
        </div>

        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {[1,2,3].map(i => (
              <div key={i}>
                <div style={{ height: '10px', background: '#1e1e2e', borderRadius: '4px', marginBottom: '4px', width: '60%' }} />
                <div style={{ height: '3px', background: '#1e1e2e', borderRadius: '2px' }} />
              </div>
            ))}
          </div>
        ) : stats ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '11px', color: '#64748b' }}>CPU</span>
                <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'JetBrains Mono, monospace' }}>
                  {stats.cpu_percent?.toFixed(1) ?? '—'}%
                </span>
              </div>
              <MiniProgress value={stats.cpu_percent ?? 0} max={100} />
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '11px', color: '#64748b' }}>RAM</span>
                <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'JetBrains Mono, monospace' }}>
                  {stats.ram_used_gb?.toFixed(1) ?? '—'}/{stats.ram_total_gb?.toFixed(0) ?? '—'} GB
                </span>
              </div>
              <MiniProgress value={stats.ram_used_gb ?? 0} max={stats.ram_total_gb ?? 1} />
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '11px', color: '#64748b' }}>Disk</span>
                <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'JetBrains Mono, monospace' }}>
                  {stats.disk_used_gb?.toFixed(0) ?? '—'}/{stats.disk_total_gb?.toFixed(0) ?? '—'} GB
                </span>
              </div>
              <MiniProgress value={stats.disk_used_gb ?? 0} max={stats.disk_total_gb ?? 1} />
            </div>
          </div>
        ) : (
          <span style={{ fontSize: '11px', color: '#475569' }}>Unavailable</span>
        )}
      </div>

      {/* Version */}
      <div style={{ padding: '8px 20px 12px', borderTop: '1px solid #1e1e2e' }}>
        <span style={{ fontSize: '10px', color: '#334155', fontFamily: 'JetBrains Mono, monospace' }}>v0.1.0</span>
      </div>
    </div>
  )
}
