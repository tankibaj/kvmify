import { Link } from 'react-router-dom'
import { Plus } from 'lucide-react'
import Button from '../ui/Button'

export default function TopBar({ title }) {
  return (
    <div
      style={{
        height: '60px',
        background: '#111118',
        borderBottom: '1px solid #1e1e2e',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      <h1 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#e2e8f0' }}>
        {title}
      </h1>
      <Link to="/provision" style={{ textDecoration: 'none' }}>
        <Button variant="primary" size="sm">
          <Plus size={14} />
          New VM
        </Button>
      </Link>
    </div>
  )
}
