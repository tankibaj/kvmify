import { Routes, Route } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { NotificationProvider } from './contexts/NotificationContext'
import Sidebar from './components/layout/Sidebar'
import NotificationToast from './components/notifications/NotificationToast'
import Dashboard from './pages/Dashboard'
import Provision from './pages/Provision'
import Images from './pages/Images'
import Pools from './pages/Pools'

// VMDetail pulls in Recharts (+ lazily noVNC); code-split it so those
// libraries don't weigh down the initial bundle for the other pages.
const VMDetail = lazy(() => import('./pages/VMDetail'))

export default function App() {
  return (
    <NotificationProvider>
      <div style={{ display: 'flex', minHeight: '100vh', background: '#0a0a0f' }}>
        <Sidebar />
        <div style={{ marginLeft: '240px', flex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <main style={{ flex: 1 }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/provision" element={<Provision />} />
              <Route path="/vms/:name" element={<Suspense fallback={null}><VMDetail /></Suspense>} />
              <Route path="/images" element={<Images />} />
              <Route path="/pools" element={<Pools />} />
            </Routes>
          </main>
        </div>
      </div>
      <NotificationToast />
    </NotificationProvider>
  )
}
