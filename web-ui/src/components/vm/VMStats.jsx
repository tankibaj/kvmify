import { useEffect, useRef, useState } from 'react'
import { useVMStats } from '../../api/client'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

const MAX_POINTS = 60

function SparklineChart({ data, dataKey, color, label, currentValue }) {
  return (
    <div
      style={{
        background: '#0a0a0f',
        border: '1px solid #1e1e2e',
        borderRadius: '12px',
        padding: '16px',
        flex: 1,
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '10px',
        }}
      >
        <span
          style={{
            fontSize: '11px',
            fontWeight: 600,
            color: '#475569',
            textTransform: 'uppercase',
            letterSpacing: '0.07em',
          }}
        >
          {label}
        </span>
        <span
          style={{
            fontSize: '18px',
            fontWeight: 700,
            color,
            fontFamily: 'JetBrains Mono, monospace',
          }}
        >
          {currentValue != null ? `${currentValue.toFixed(1)}%` : '—'}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={72}>
        <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`grad-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.25} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="t" hide />
          <YAxis domain={[0, 100]} hide />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              return (
                <div
                  style={{
                    background: '#1e1e2e',
                    border: '1px solid #2e2e4e',
                    borderRadius: '6px',
                    padding: '4px 8px',
                    fontSize: '11px',
                    color: '#e2e8f0',
                    fontFamily: 'JetBrains Mono, monospace',
                  }}
                >
                  {payload[0].value?.toFixed(1)}%
                </div>
              )
            }}
          />
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#grad-${dataKey})`}
            isAnimationActive={false}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function VMStats({ vmName }) {
  const { data } = useVMStats(vmName)
  const bufferRef = useRef([])
  const tickRef = useRef(0)
  const [chartData, setChartData] = useState([])

  useEffect(() => {
    if (!data) return
    const point = {
      t: tickRef.current++,
      cpu: data.cpu_percent ?? null,
      ram: data.ram_percent ?? null,
    }
    bufferRef.current = [...bufferRef.current, point].slice(-MAX_POINTS)
    setChartData([...bufferRef.current])
  }, [data])

  const latest = chartData[chartData.length - 1]

  return (
    <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
      <SparklineChart
        data={chartData}
        dataKey="cpu"
        color="#6366f1"
        label="CPU Usage"
        currentValue={latest?.cpu}
      />
      <SparklineChart
        data={chartData}
        dataKey="ram"
        color="#10b981"
        label="RAM Usage"
        currentValue={latest?.ram}
      />
    </div>
  )
}
