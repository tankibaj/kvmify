import TopBar from '../components/layout/TopBar'
import { Card } from '../components/ui'

export default function Provision() {
  return (
    <div>
      <TopBar title="Provision VM" />
      <div style={{ padding: '24px', maxWidth: '720px' }}>
        <Card title="New Virtual Machine">
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#475569', fontSize: '13px' }}>
            Provision form coming in Phase 2.
          </div>
        </Card>
      </div>
    </div>
  )
}
