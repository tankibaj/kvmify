import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useVM } from '../api/client'
import { StatusDot } from '../components/ui'
import VMOverview from '../components/vm/VMOverview'
import VMConsole from '../components/vm/VMConsole'
import SnapshotList from '../components/vm/SnapshotList'
import VMNetwork from '../components/vm/VMNetwork'
import VMResize from '../components/vm/VMResize'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'console', label: 'Console' },
  { id: 'snapshots', label: 'Snapshots' },
  { id: 'network', label: 'Network' },
  { id: 'resize', label: 'Resize' },
]

const VALID_TAB_IDS = new Set(TABS.map((t) => t.id))

export default function VMDetail() {
  const { name } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()

  // Deep-link support: ?tab=console|snapshots|resize|network
  const initialTab = (() => {
    const p = searchParams.get('tab')
    return p && VALID_TAB_IDS.has(p) ? p : 'overview'
  })()

  const [activeTab, setActiveTab] = useState(initialTab)

  function switchTab(id) {
    setActiveTab(id)
    if (id === 'overview') {
      setSearchParams({}, { replace: true })
    } else {
      setSearchParams({ tab: id }, { replace: true })
    }
  }

  const { data: vm, isLoading } = useVM(name)

  return (
    <div>
      {/* Top bar */}
      <div
        style={{
          height: '60px',
          background: '#111118',
          borderBottom: '1px solid #1e1e2e',
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          position: 'sticky',
          top: 0,
          zIndex: 50,
          gap: '10px',
        }}
      >
        <StatusDot status={vm?.state ?? 'stopped'} />
        <h1
          style={{
            margin: 0,
            fontSize: '16px',
            fontWeight: 600,
            color: '#e2e8f0',
            fontFamily: 'JetBrains Mono, monospace',
          }}
        >
          {name}
        </h1>
        {vm?.state && (
          <span
            style={{
              fontSize: '12px',
              color: '#64748b',
              textTransform: 'capitalize',
            }}
          >
            {vm.state}
          </span>
        )}
      </div>

      {/* Tab bar */}
      <div
        style={{
          background: '#111118',
          borderBottom: '1px solid #1e1e2e',
          padding: '0 24px',
          display: 'flex',
          gap: '0',
        }}
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => switchTab(tab.id)}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: isActive
                  ? '2px solid #6366f1'
                  : '2px solid transparent',
                color: isActive ? '#6366f1' : '#64748b',
                padding: '12px 16px',
                fontSize: '13px',
                fontWeight: isActive ? 600 : 400,
                cursor: 'pointer',
                transition: 'all 150ms ease',
                fontFamily: 'inherit',
                outline: 'none',
                whiteSpace: 'nowrap',
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.color = '#94a3b8'
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.color = '#64748b'
              }}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      <div style={{ padding: '24px', maxWidth: '1000px' }}>
        {isLoading ? (
          <div
            style={{
              padding: '60px 0',
              textAlign: 'center',
              color: '#475569',
              fontSize: '13px',
            }}
          >
            Loading VM…
          </div>
        ) : !vm ? (
          <div
            style={{
              padding: '60px 0',
              textAlign: 'center',
              color: '#475569',
              fontSize: '13px',
            }}
          >
            VM not found.
          </div>
        ) : (
          <>
            {activeTab === 'overview' && <VMOverview vm={vm} />}
            {activeTab === 'console' && <VMConsole vmName={name} />}
            {activeTab === 'snapshots' && <SnapshotList vmName={name} />}
            {activeTab === 'network' && <VMNetwork vm={vm} />}
            {activeTab === 'resize' && <VMResize vm={vm} />}
          </>
        )}
      </div>
    </div>
  )
}
