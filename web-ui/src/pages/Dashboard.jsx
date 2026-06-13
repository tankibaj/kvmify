import TopBar from '../components/layout/TopBar'
import { Card } from '../components/ui'

function StatCard({ label, value, sub }) {
  return (
    <Card>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <span style={{ fontSize: '11px', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
        <span style={{ fontSize: '28px', fontWeight: 700, color: '#e2e8f0', fontFamily: 'JetBrains Mono, monospace', lineHeight: 1.2 }}>{value}</span>
        {sub && <span style={{ fontSize: '12px', color: '#64748b' }}>{sub}</span>}
      </div>
    </Card>
  )
}

export default function Dashboard() {
  return (
    <div>
      <TopBar title="Dashboard" />
      <div style={{ padding: '24px', maxWidth: '1200px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
          <StatCard label="Total VMs" value="—" sub="Loading..." />
          <StatCard label="Running" value="—" sub="Loading..." />
          <StatCard label="Stopped" value="—" sub="Loading..." />
          <StatCard label="Host CPU" value="—" sub="Loading..." />
        </div>
        <Card title="Virtual Machines">
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#475569', fontSize: '13px' }}>
            No VMs yet. <a href="/provision" style={{ color: '#6366f1', textDecoration: 'none' }}>Provision your first VM →</a>
          </div>
        </Card>
      </div>
    </div>
  )
}
