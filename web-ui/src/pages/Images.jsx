import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, Loader2 } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import { Button, Card, Badge, CopyButton } from '../components/ui'
import { useImages, useSyncImages } from '../api/client'
import { useNotify } from '../contexts/NotificationContext'

function formatBytes(bytes) {
  if (bytes == null) return '—'
  return (bytes / (1024 ** 3)).toFixed(1) + ' GiB'
}

function formatRelativeTime(iso) {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 30) return `${days} days ago`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months} month${months > 1 ? 's' : ''} ago`
  const years = Math.floor(months / 12)
  return `${years} year${years > 1 ? 's' : ''} ago`
}

function statusBadgeVariant(status) {
  if (status === 'up_to_date') return 'running'
  if (status === 'outdated') return 'provisioning'
  if (status === 'missing') return 'error'
  return 'default'
}

function statusLabel(status) {
  if (status === 'up_to_date') return 'Up to date'
  if (status === 'outdated') return 'Outdated'
  if (status === 'missing') return 'Missing'
  return 'Unknown'
}

export default function Images() {
  const { data: images = [], isLoading, error: imagesError } = useImages()
  const syncAllMutation = useSyncImages()
  const notify = useNotify()
  const [syncingVersions, setSyncingVersions] = useState({})

  const syncStatusQuery = useQuery({
    queryKey: ['image-sync-status'],
    queryFn: () => fetch('/api/images/sync/status').then(r => r.json()),
    refetchInterval: (query) => query.state.data?.state === 'running' ? 2000 : 10000,
  })
  const syncStatus = syncStatusQuery.data
  const syncRunning = syncStatus?.state === 'running'

  const logRef = useRef(null)
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [syncStatus?.log])

  const handleSyncAll = () => syncAllMutation.mutate()

  // Per-row sync reuses the same mutation, passing the version key in the body.
  const handleSyncOne = (version) => {
    setSyncingVersions(p => ({ ...p, [version]: true }))
    syncAllMutation.mutate(version, {
      onSettled: () => setSyncingVersions(p => ({ ...p, [version]: false })),
    })
  }

  const thStyle = {
    textAlign: 'left',
    padding: '8px 16px',
    fontSize: '11px',
    fontWeight: 600,
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    borderBottom: '1px solid #1e1e2e',
    whiteSpace: 'nowrap',
  }

  const tdStyle = {
    padding: '12px 16px',
    fontSize: '13px',
    color: '#e2e8f0',
    verticalAlign: 'middle',
  }

  return (
    <div>
      <TopBar title="Base Images" />
      <div style={{ padding: '24px', maxWidth: '1100px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#e2e8f0' }}>Ubuntu Base Images</h2>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSyncAll}
            disabled={syncRunning || syncAllMutation.isPending}
            loading={syncAllMutation.isPending}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} />
            Sync All
          </Button>
        </div>

        <Card style={{ overflow: 'hidden' }}>
          {isLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0', gap: '10px', color: '#475569', fontSize: '13px' }}>
              <Loader2 size={16} style={{ animation: 'spin 1s linear infinite', color: '#6366f1' }} />
              Loading images…
            </div>
          ) : imagesError ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#f43f5e', fontSize: '13px' }}>
              Failed to load images. Check API connectivity.
            </div>
          ) : images.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#475569', fontSize: '13px' }}>
              No base images found. Run a sync to fetch them.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={thStyle}>Version</th>
                  <th style={thStyle}>Codename</th>
                  <th style={{ ...thStyle, fontFamily: 'JetBrains Mono, monospace' }}>Size</th>
                  <th style={thStyle}>Last Updated</th>
                  <th style={thStyle}>Checksum</th>
                  <th style={thStyle}>Status</th>
                  <th style={{ ...thStyle, textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {images.map((img) => (
                  <tr
                    key={img.version}
                    style={{ borderBottom: '1px solid #1e1e2e' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(30,30,46,0.5)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={tdStyle}>
                      <span style={{ fontWeight: 600, color: '#e2e8f0' }}>{img.label || `Ubuntu ${img.version}`}</span>
                    </td>
                    <td style={{ ...tdStyle, color: '#94a3b8', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>
                      {img.codename || '—'}
                    </td>
                    <td style={{ ...tdStyle, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: '#94a3b8' }}>
                      {formatBytes(img.size)}
                    </td>
                    <td style={{ ...tdStyle, color: '#94a3b8', fontSize: '12px' }}>
                      {formatRelativeTime(img.last_updated)}
                    </td>
                    <td style={{ ...tdStyle, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: '#94a3b8' }}>
                      {img.checksum ? (
                        <CopyButton
                          text={img.checksum}
                          label={img.checksum.slice(0, 16) + '…'}
                        />
                      ) : '—'}
                    </td>
                    <td style={tdStyle}>
                      <Badge variant={statusBadgeVariant(img.status)}>
                        {statusLabel(img.status)}
                      </Badge>
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'right' }}>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleSyncOne(img.version)}
                        disabled={syncRunning || !!syncingVersions[img.version]}
                        loading={!!syncingVersions[img.version]}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      >
                        <RefreshCw size={12} />
                        Sync
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        {syncStatus?.log != null && (
          <div style={{ marginTop: '16px', background: '#0a0a0f', border: '1px solid #1e1e2e', borderRadius: '12px', overflow: 'hidden' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 16px', borderBottom: '1px solid #1e1e2e' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Sync Log</span>
              {syncRunning && (
                <Loader2 size={12} style={{ color: '#6366f1', animation: 'spin 1s linear infinite' }} />
              )}
              <Badge variant={syncStatus.state === 'success' ? 'running' : syncStatus.state === 'error' ? 'error' : 'provisioning'}>
                {syncStatus.state}
              </Badge>
              {syncStatus.version && (
                <span style={{ fontSize: '11px', color: '#475569', fontFamily: 'JetBrains Mono, monospace' }}>
                  v{syncStatus.version}
                </span>
              )}
              {syncStatus.finished_at && (
                <span style={{ fontSize: '11px', color: '#475569', marginLeft: 'auto' }}>
                  Finished {formatRelativeTime(syncStatus.finished_at)}
                </span>
              )}
              {!syncStatus.finished_at && syncStatus.started_at && (
                <span style={{ fontSize: '11px', color: '#475569', marginLeft: 'auto' }}>
                  Started {formatRelativeTime(syncStatus.started_at)}
                </span>
              )}
            </div>
            <div
              ref={logRef}
              style={{
                padding: '12px 16px',
                maxHeight: '220px',
                overflowY: 'auto',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '12px',
                color: '#10b981',
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {syncStatus.log || '(no output)'}
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
