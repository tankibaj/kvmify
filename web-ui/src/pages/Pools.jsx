import TopBar from '../components/layout/TopBar'
import { Card } from '../components/ui'

export default function Pools() {
  return (
    <div>
      <TopBar title="Storage Pools" />
      <div style={{ padding: '24px', maxWidth: '1000px' }}>
        <Card title="Storage Pools">
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#475569', fontSize: '13px' }}>
            Pool management coming in Phase 2.
          </div>
        </Card>
      </div>
    </div>
  )
}
