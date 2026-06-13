import TopBar from '../components/layout/TopBar'
import { Card } from '../components/ui'

export default function Images() {
  return (
    <div>
      <TopBar title="Base Images" />
      <div style={{ padding: '24px', maxWidth: '1000px' }}>
        <Card title="Available Images">
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#475569', fontSize: '13px' }}>
            Image management coming in Phase 2.
          </div>
        </Card>
      </div>
    </div>
  )
}
