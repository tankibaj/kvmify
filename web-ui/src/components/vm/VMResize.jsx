import { useState } from 'react'
import { useResizeVM } from '../../api/client'
import { Slider, Button } from '../ui'
import { AlertTriangle, Save } from 'lucide-react'

const CPU_OPTIONS = [1, 2, 4, 8]
const RAM_OPTIONS = [512, 1024, 2048, 4096, 8192]
const DISK_OPTIONS = [10, 20, 50, 100]

function snapToNearest(value, options) {
  return options.reduce((prev, cur) =>
    Math.abs(cur - value) < Math.abs(prev - value) ? cur : prev
  )
}

function DiscreteSlider({ label, options, value, onChange, formatLabel }) {
  const idx = options.indexOf(value)
  const displayIdx = idx === -1 ? 0 : idx

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span style={{ fontSize: '12px', fontWeight: 500, color: '#94a3b8' }}>
          {label}
        </span>
        <span
          style={{
            fontSize: '13px',
            fontWeight: 600,
            color: '#6366f1',
            fontFamily: 'JetBrains Mono, monospace',
          }}
        >
          {formatLabel(value)}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={options.length - 1}
        step={1}
        value={displayIdx}
        onChange={(e) => onChange(options[Number(e.target.value)])}
        style={{
          appearance: 'none',
          width: '100%',
          height: '4px',
          borderRadius: '2px',
          background: `linear-gradient(to right, #6366f1 ${(displayIdx / (options.length - 1)) * 100}%, #1e1e2e ${(displayIdx / (options.length - 1)) * 100}%)`,
          outline: 'none',
          cursor: 'pointer',
        }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        {options.map((o) => (
          <span key={o} style={{ fontSize: '10px', color: '#475569' }}>
            {formatLabel(o)}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function VMResize({ vm }) {
  const resizeVM = useResizeVM()

  const [cpu, setCpu] = useState(
    () => snapToNearest(vm?.vcpus ?? 1, CPU_OPTIONS)
  )
  const [ram, setRam] = useState(
    () => snapToNearest(vm?.ram_mb ?? 1024, RAM_OPTIONS)
  )
  const [disk, setDisk] = useState(
    () => snapToNearest(vm?.disk_gb ?? 20, DISK_OPTIONS)
  )

  function handleApply() {
    resizeVM.mutate({ name: vm.name, cpu, ram_mb: ram, disk_gb: disk })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Current values */}
      <div
        style={{
          background: '#0a0a0f',
          border: '1px solid #1e1e2e',
          borderRadius: '10px',
          padding: '16px',
          display: 'flex',
          gap: '24px',
          flexWrap: 'wrap',
        }}
      >
        {[
          { label: 'CPU', current: `${vm?.vcpus ?? '—'} vCPUs`, next: `${cpu} vCPUs` },
          {
            label: 'RAM',
            current: `${vm?.ram_mb ? (vm.ram_mb / 1024).toFixed(1) : '—'} GB`,
            next: `${(ram / 1024).toFixed(1)} GB`,
          },
          {
            label: 'Disk',
            current: `${vm?.disk_gb ?? '—'} GB`,
            next: `${disk} GB`,
          },
        ].map(({ label, current, next }) => (
          <div key={label} style={{ flex: 1, minWidth: '100px' }}>
            <div
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: '#475569',
                textTransform: 'uppercase',
                letterSpacing: '0.07em',
                marginBottom: '4px',
              }}
            >
              {label}
            </div>
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '14px',
                color: '#94a3b8',
                textDecoration: 'line-through',
              }}
            >
              {current}
            </div>
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '16px',
                fontWeight: 700,
                color: '#6366f1',
              }}
            >
              {next}
            </div>
          </div>
        ))}
      </div>

      {/* CPU + RAM amber warning */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '10px',
          background: 'rgba(245,158,11,0.08)',
          border: '1px solid rgba(245,158,11,0.25)',
          borderRadius: '8px',
          padding: '12px 14px',
        }}
      >
        <AlertTriangle
          size={14}
          style={{ color: '#f59e0b', flexShrink: 0, marginTop: '1px' }}
        />
        <div style={{ fontSize: '12px', color: '#f59e0b', lineHeight: 1.5 }}>
          <strong>CPU and RAM resize requires the VM to be stopped.</strong>
          <br />
          Disk resize is applied online.
        </div>
      </div>

      {/* Sliders */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
          background: '#111118',
          border: '1px solid #1e1e2e',
          borderRadius: '10px',
          padding: '20px',
        }}
      >
        <DiscreteSlider
          label="CPU (vCPUs)"
          options={CPU_OPTIONS}
          value={cpu}
          onChange={setCpu}
          formatLabel={(v) => `${v} vCPU${v > 1 ? 's' : ''}`}
        />
        <DiscreteSlider
          label="RAM"
          options={RAM_OPTIONS}
          value={ram}
          onChange={setRam}
          formatLabel={(v) => (v >= 1024 ? `${v / 1024} GB` : `${v} MB`)}
        />
        <DiscreteSlider
          label="Disk"
          options={DISK_OPTIONS}
          value={disk}
          onChange={setDisk}
          formatLabel={(v) => `${v} GB`}
        />
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="primary"
          size="sm"
          loading={resizeVM.isPending}
          onClick={handleApply}
        >
          <Save size={13} />
          Apply Changes
        </Button>
      </div>
    </div>
  )
}
