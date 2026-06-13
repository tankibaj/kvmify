import { useEffect, useRef, useState } from 'react'
import { useVMConsole } from '../../api/client'
import { Button } from '../ui'
import { Maximize2, Minimize2, Clipboard } from 'lucide-react'

// ── VNC URL builder ── Phase 4 will proxy /novnc → websockify on the host.
// Keep this function isolated so Phase 4 can update just this one line.
function buildVncUrl(port) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/novnc/?port=${port}`
}

const STATUS = {
  IDLE: 'idle',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  ERROR: 'error',
}

export default function VMConsole({ vmName }) {
  const { data: consoleData, isLoading, isError } = useVMConsole(vmName)
  const canvasRef = useRef(null)
  const rfbRef = useRef(null)
  const [status, setStatus] = useState(STATUS.IDLE)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const containerRef = useRef(null)

  useEffect(() => {
    if (!consoleData?.vnc_port || !canvasRef.current) return

    let rfb = null

    async function connect() {
      try {
        // @novnc/novnc exports only its root (./core/rfb.js) via the bare specifier
        const { default: RFB } = await import('@novnc/novnc')
        setStatus(STATUS.CONNECTING)

        rfb = new RFB(canvasRef.current, buildVncUrl(consoleData.vnc_port))
        rfbRef.current = rfb

        rfb.scaleViewport = true
        rfb.resizeSession = false

        rfb.addEventListener('connect', () => setStatus(STATUS.CONNECTED))
        rfb.addEventListener('disconnect', () => {
          setStatus(STATUS.DISCONNECTED)
          rfbRef.current = null
        })
        rfb.addEventListener('securityfailure', () => {
          setStatus(STATUS.ERROR)
          rfbRef.current = null
        })
      } catch (err) {
        // noVNC import or connection failed — show graceful state
        setStatus(STATUS.ERROR)
      }
    }

    connect()

    return () => {
      try {
        rfb?.disconnect()
      } catch {
        /* ignore cleanup errors */
      }
      rfbRef.current = null
    }
  }, [consoleData?.vnc_port])

  // Fullscreen toggle
  useEffect(() => {
    function onFsChange() {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', onFsChange)
    return () => document.removeEventListener('fullscreenchange', onFsChange)
  }, [])

  function handleCtrlAltDel() {
    rfbRef.current?.sendCtrlAltDel()
  }

  function handleFullscreen() {
    if (!isFullscreen) {
      containerRef.current?.requestFullscreen?.()
    } else {
      document.exitFullscreen?.()
    }
  }

  async function handleClipboardPaste() {
    try {
      const text = await navigator.clipboard.readText()
      rfbRef.current?.clipboardPasteFrom(text)
    } catch {
      /* clipboard permission denied */
    }
  }

  const statusColor = {
    [STATUS.IDLE]: '#64748b',
    [STATUS.CONNECTING]: '#f59e0b',
    [STATUS.CONNECTED]: '#10b981',
    [STATUS.DISCONNECTED]: '#f43f5e',
    [STATUS.ERROR]: '#f43f5e',
  }[status]

  const statusLabel = {
    [STATUS.IDLE]: 'Idle',
    [STATUS.CONNECTING]: 'Connecting…',
    [STATUS.CONNECTED]: 'Connected',
    [STATUS.DISCONNECTED]: 'Disconnected',
    [STATUS.ERROR]: 'Unavailable',
  }[status]

  const isConnected = status === STATUS.CONNECTED

  // Graceful unavailable state
  const unavailable =
    isError ||
    status === STATUS.ERROR ||
    status === STATUS.DISCONNECTED ||
    (!isLoading && !consoleData?.vnc_port)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '10px 16px',
          background: '#111118',
          border: '1px solid #1e1e2e',
          borderRadius: '10px',
        }}
      >
        {/* Status indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1 }}>
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: statusColor,
              flexShrink: 0,
              display: 'inline-block',
            }}
          />
          <span style={{ fontSize: '12px', color: '#94a3b8' }}>{statusLabel}</span>
        </div>

        <Button
          variant="ghost"
          size="sm"
          disabled={!isConnected}
          onClick={handleCtrlAltDel}
        >
          Ctrl+Alt+Del
        </Button>
        <Button
          variant="ghost"
          size="sm"
          disabled={!isConnected}
          onClick={handleClipboardPaste}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
        >
          <Clipboard size={12} />
          Paste
        </Button>
        <Button variant="ghost" size="sm" onClick={handleFullscreen}>
          {isFullscreen ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
        </Button>
      </div>

      {/* Canvas area */}
      <div
        ref={containerRef}
        style={{
          position: 'relative',
          background: '#000',
          border: '1px solid #1e1e2e',
          borderRadius: '12px',
          overflow: 'hidden',
          minHeight: '480px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* noVNC canvas target */}
        <div
          ref={canvasRef}
          style={{
            width: '100%',
            height: '100%',
            minHeight: '480px',
            display: unavailable || status === STATUS.CONNECTING ? 'none' : 'block',
          }}
        />

        {/* Overlay states */}
        {(unavailable || status === STATUS.CONNECTING || isLoading) && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              padding: '48px',
              color: '#64748b',
            }}
          >
            {isLoading || status === STATUS.CONNECTING ? (
              <>
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    border: '2px solid #1e1e2e',
                    borderTopColor: '#6366f1',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite',
                  }}
                />
                <span style={{ fontSize: '13px' }}>
                  {isLoading ? 'Fetching console info…' : 'Connecting to console…'}
                </span>
              </>
            ) : (
              <>
                <svg
                  width="40"
                  height="40"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#475569"
                  strokeWidth="1.5"
                >
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <line x1="8" y1="21" x2="16" y2="21" />
                  <line x1="12" y1="17" x2="12" y2="21" />
                </svg>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '14px', color: '#94a3b8', fontWeight: 500 }}>
                    Console unavailable
                  </div>
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>
                    The VNC proxy is not reachable. This will be connected in Phase 4.
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
