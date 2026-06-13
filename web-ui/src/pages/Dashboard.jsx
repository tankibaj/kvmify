import { Link } from 'react-router-dom'
import { Plus } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import { Card, Button } from '../components/ui'
import { useVMs } from '../api/client'
import VMTable from '../components/vm/VMTable'

function StatCard({ label, value, sub }) {
  return (
    <Card>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <span style={{
          fontSize: 11,
          fontWeight: 600,
          color: '#475569',
          textTransform: 'uppercase',
          letterSpacing: '0.07em',
        }}>
          {label}
        </span>
        <span style={{
          fontSize: 28,
          fontWeight: 700,
          color: '#e2e8f0',
          fontFamily: 'JetBrains Mono, monospace',
          lineHeight: 1.2,
        }}>
          {value}
        </span>
        {sub && <span style={{ fontSize: 12, color: '#64748b' }}>{sub}</span>}
      </div>
    </Card>
  )
}

export default function Dashboard() {
  const { data: vms, isLoading } = useVMs()

  const totalVMs = vms?.length ?? 0
  const running = vms?.filter(v => v.state === 'running').length ?? 0
  const stopped = vms?.filter(v => v.state === 'shutoff' || v.state === 'stopped').length ?? 0
  const totalRamGB = vms
    ? (vms.reduce((sum, v) => sum + (v.ram_mb ?? 0), 0) / 1024).toFixed(1)
    : '0.0'

  return (
    <div>
      {/* Top bar with custom action button */}
      <div style={{
        height: 60,
        background: '#111118',
        borderBottom: '1px solid #1e1e2e',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}>
        <h1 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#e2e8f0' }}>
          Virtual Machines
        </h1>
        <Link to="/provision" style={{ textDecoration: 'none' }}>
          <Button variant="primary" size="sm">
            <Plus size={14} />
            New VM
          </Button>
        </Link>
      </div>

      <div style={{ padding: 24 }}>
        {/* Stats bar */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
          gap: 16,
          marginBottom: 24,
        }}>
          <StatCard
            label="Total VMs"
            value={isLoading ? '—' : totalVMs}
            sub={isLoading ? 'Loading…' : totalVMs === 1 ? '1 machine' : `${totalVMs} machines`}
          />
          <StatCard
            label="Running"
            value={isLoading ? '—' : running}
            sub={running > 0 ? 'Active' : 'None active'}
          />
          <StatCard
            label="Stopped"
            value={isLoading ? '—' : stopped}
            sub={stopped > 0 ? 'Idle' : 'All running'}
          />
          <StatCard
            label="RAM Allocated"
            value={isLoading ? '—' : `${totalRamGB} GB`}
            sub="Total across all VMs"
          />
        </div>

        {/* VM table */}
        <Card title="Virtual Machines">
          {isLoading ? (
            <div style={{ padding: '40px 0', textAlign: 'center', color: '#475569', fontSize: 13 }}>
              Loading virtual machines…
            </div>
          ) : (
            <VMTable vms={vms ?? []} />
          )}
        </Card>
      </div>
    </div>
  )
}
