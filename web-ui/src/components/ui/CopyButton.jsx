import { useState } from 'react'
import { Clipboard, Check } from 'lucide-react'

export default function CopyButton({ text, label }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback
    }
  }

  return (
    <button
      onClick={handleCopy}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        background: '#1e1e2e',
        border: '1px solid #2e2e4e',
        borderRadius: '6px',
        padding: '4px 10px',
        cursor: 'pointer',
        transition: 'all 150ms ease',
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: '12px',
        color: '#94a3b8',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = '#6366f1'
        e.currentTarget.style.color = '#e2e8f0'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = '#2e2e4e'
        e.currentTarget.style.color = '#94a3b8'
      }}
    >
      {copied
        ? <Check size={12} style={{ color: '#10b981' }} />
        : <Clipboard size={12} />
      }
      <span>{label ?? text}</span>
    </button>
  )
}
