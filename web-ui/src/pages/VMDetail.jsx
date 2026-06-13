import { useParams } from 'react-router-dom'
import TopBar from '../components/layout/TopBar'
import { Card } from '../components/ui'

export default function VMDetail() {
  const { name } = useParams()
  return (
    <div>
      <TopBar title={name ?? 'VM Detail'} />
      <div style={{ padding: '24px', maxWidth: '1000px' }}>
        <Card title="VM Overview">
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#475569', fontSize: '13px' }}>
            VM detail view coming in Phase 2.
          </div>
        </Card>
      </div>
    </div>
  )
}
