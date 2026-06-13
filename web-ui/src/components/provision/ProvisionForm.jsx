import { useState, useEffect, useRef } from 'react'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { Button, Input, Select, Slider, CopyButton } from '../ui'
import { useNetworks, usePools, useProvisionVM } from '../../api/client'
import NetworkConfig, { validateNetworkConfig } from './NetworkConfig'

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatBytes(bytes) {
  return bytes >= 1e9
    ? (bytes / 1e9).toFixed(0) + ' GB'
    : (bytes / 1e6).toFixed(0) + ' MB'
}

function formatRam(mb) {
  if (mb >= 1024) {
    return mb / 1024 % 1 === 0
      ? mb / 1024 + ' GB'
      : (mb / 1024).toFixed(1) + ' GB'
  }
  return mb + ' MB'
}

const UBUNTU_LABELS = {
  '2004': 'Ubuntu 20.04',
  '2204': 'Ubuntu 22.04',
  '2404': 'Ubuntu 24.04',
}

const PROVISION_STEPS = [
  'Cloning base image',
  'Generating cloud-init',
  'Configuring network',
  'Starting VM',
  'Waiting for IP…',
  'Ready',
]

// ─── Sub-components ──────────────────────────────────────────────────────────

function SummaryRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
      <span style={{ fontSize: 12, color: '#64748b', flexShrink: 0 }}>{label}</span>
      <span style={{ fontSize: 13, color: '#e2e8f0', fontFamily: 'JetBrains Mono, monospace', textAlign: 'right', wordBreak: 'break-all' }}>
        {value}
      </span>
    </div>
  )
}

function SectionHeader({ children }) {
  return (
    <div style={{
      fontSize: 11,
      fontWeight: 600,
      color: '#475569',
      textTransform: 'uppercase',
      letterSpacing: '0.07em',
      marginBottom: 16,
    }}>
      {children}
    </div>
  )
}

function PresetButtons({ values, labels, active, onSelect, max }) {
  return (
    <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
      {values.map((v, i) => {
        const clamped = max !== undefined ? Math.min(v, max) : v
        const isActive = active === clamped
        return (
          <Button
            key={v}
            variant="ghost"
            size="sm"
            style={{
              opacity: isActive ? 1 : 0.6,
              borderColor: isActive ? '#6366f1' : '#1e1e2e',
              color: isActive ? '#6366f1' : '#94a3b8',
            }}
            onClick={() => onSelect(clamped)}
          >
            {labels ? labels[i] : v}
          </Button>
        )
      })}
    </div>
  )
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function ProvisionForm() {
  const [form, setForm] = useState({
    vm_name: '',
    ubuntu_version: '2204',
    cpu: 2,
    ram_mb: 2048,
    disk_gb: 20,
    storage_pool: '',
    ssh_public_key: '',
    network: '',
    ip_mode: 'dhcp',
    static_ip: '',
    subnet_mask: '255.255.255.0',
    gateway: '',
    dns: '8.8.8.8',
  })
  const [errors, setErrors] = useState({})
  const [submitted, setSubmitted] = useState(false)
  const [provisionResult, setProvisionResult] = useState(null)
  const [stepIndex, setStepIndex] = useState(0)

  const { data: networksData } = useNetworks()
  const { data: pools } = usePools()
  const provision = useProvisionVM()

  // Auto-select default pool
  useEffect(() => {
    if (pools && pools.length > 0 && !form.storage_pool) {
      const def = pools.find(p => p.is_default) || pools[0]
      if (def) setForm(f => ({ ...f, storage_pool: def.name }))
    }
  }, [pools])

  // Step animation while pending
  const intervalRef = useRef(null)
  useEffect(() => {
    if (provision.isPending) {
      setStepIndex(0)
      intervalRef.current = setInterval(() => {
        setStepIndex(i => Math.min(i + 1, PROVISION_STEPS.length - 2))
      }, 4000)
    } else {
      clearInterval(intervalRef.current)
      if (provisionResult) setStepIndex(PROVISION_STEPS.length - 1)
    }
    return () => clearInterval(intervalRef.current)
  }, [provision.isPending, provisionResult])

  const selectedPool = pools?.find(p => p.name === form.storage_pool)
  const diskMax = Math.max(10, Math.min(100, selectedPool
    ? Math.floor(selectedPool.available / 1e9)
    : 100))

  const selectedNetwork = networksData?.find(n => n.id === form.network)

  function validate() {
    const errs = {}
    if (!form.vm_name) {
      errs.vm_name = 'VM name is required'
    } else if (!/^[a-z][a-z0-9-]*$/.test(form.vm_name)) {
      errs.vm_name = 'Lowercase letters, numbers, hyphens only; must start with a letter'
    } else if (form.vm_name.length > 32) {
      errs.vm_name = 'Max 32 characters'
    }
    if (!form.storage_pool) errs.storage_pool = 'Select a storage pool'
    if (!form.ssh_public_key.trim()) errs.ssh_public_key = 'SSH public key is required'
    const { valid: netValid, errors: netErrors } = validateNetworkConfig({
      network: form.network,
      ip_mode: form.ip_mode,
      static_ip: form.static_ip,
      subnet_mask: form.subnet_mask,
      gateway: form.gateway,
      dns: form.dns,
    })
    if (!netValid) Object.assign(errs, netErrors)
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  function handleSubmit() {
    setSubmitted(true)
    if (!validate()) return
    const payload = {
      vm_name: form.vm_name,
      ubuntu_version: form.ubuntu_version,
      cpu: form.cpu,
      ram_mb: form.ram_mb,
      disk_gb: form.disk_gb,
      ssh_public_key: form.ssh_public_key,
      network: form.network,
      ip_mode: form.ip_mode,
      storage_pool: form.storage_pool,
      ...(form.ip_mode === 'static' ? {
        static_ip: form.static_ip,
        subnet_mask: form.subnet_mask,
        gateway: form.gateway,
        dns: form.dns,
      } : {}),
    }
    provision.mutate(payload, {
      onSuccess: (data) => setProvisionResult(data),
    })
  }

  function handleNetworkChange(next) {
    setForm(f => ({ ...f, ...next }))
  }

  const networkConfigValue = {
    network: form.network,
    ip_mode: form.ip_mode,
    static_ip: form.static_ip,
    subnet_mask: form.subnet_mask,
    gateway: form.gateway,
    dns: form.dns,
  }

  const showProgress = provision.isPending || provisionResult !== null

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 360px',
      gap: 24,
      alignItems: 'start',
    }}>
      {/* ── Left column ── */}
      <div>

        {/* General */}
        <div style={{ marginBottom: 32 }}>
          <SectionHeader>General</SectionHeader>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Input
              label="VM Name"
              id="vm-name"
              placeholder="my-web-server"
              value={form.vm_name}
              onChange={e => setForm(f => ({ ...f, vm_name: e.target.value }))}
              error={errors.vm_name}
            />
            <Select
              label="Ubuntu Version"
              id="ubuntu-version"
              value={form.ubuntu_version}
              onChange={e => setForm(f => ({ ...f, ubuntu_version: e.target.value }))}
            >
              <option value="2004">20.04 LTS Focal Fossa</option>
              <option value="2204">22.04 LTS Jammy Jellyfish</option>
              <option value="2404">24.04 LTS Noble Numbat</option>
            </Select>
          </div>
        </div>

        {/* Resources */}
        <div style={{ marginBottom: 32 }}>
          <SectionHeader>Resources</SectionHeader>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* CPU */}
            <div>
              <Slider
                min={1}
                max={8}
                step={1}
                value={form.cpu}
                onChange={v => setForm(f => ({ ...f, cpu: v }))}
                label="CPU Cores"
                unit="vCPU"
              />
              <PresetButtons
                values={[1, 2, 4, 8]}
                active={form.cpu}
                onSelect={v => setForm(f => ({ ...f, cpu: v }))}
              />
            </div>

            {/* RAM */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 500, color: '#94a3b8' }}>Memory</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: '#6366f1', fontFamily: 'JetBrains Mono, monospace' }}>
                  {formatRam(form.ram_mb)}
                </span>
              </div>
              <Slider
                min={512}
                max={8192}
                step={512}
                value={form.ram_mb}
                onChange={v => setForm(f => ({ ...f, ram_mb: v }))}
              />
              <PresetButtons
                values={[512, 1024, 2048, 4096, 8192]}
                labels={['512 MB', '1 GB', '2 GB', '4 GB', '8 GB']}
                active={form.ram_mb}
                onSelect={v => setForm(f => ({ ...f, ram_mb: v }))}
              />
            </div>

            {/* Disk */}
            <div>
              <Slider
                min={10}
                max={diskMax}
                step={10}
                value={Math.min(form.disk_gb, diskMax)}
                onChange={v => setForm(f => ({ ...f, disk_gb: v }))}
                label="Disk Size"
                unit="GB"
              />
              <PresetButtons
                values={[10, 20, 50, 100]}
                labels={['10 GB', '20 GB', '50 GB', '100 GB']}
                active={form.disk_gb}
                onSelect={v => setForm(f => ({ ...f, disk_gb: v }))}
                max={diskMax}
              />
            </div>

            {/* Storage Pool */}
            <Select
              label="Storage Pool"
              id="storage-pool"
              value={form.storage_pool}
              onChange={e => setForm(f => ({ ...f, storage_pool: e.target.value }))}
              error={errors.storage_pool}
            >
              {!form.storage_pool && <option value="">Select pool…</option>}
              {(pools || []).map(p => (
                <option key={p.name} value={p.name}>
                  {p.name} — {formatBytes(p.available)} free
                </option>
              ))}
            </Select>

          </div>
        </div>

        {/* Network */}
        <div style={{ marginBottom: 32 }}>
          <SectionHeader>Network</SectionHeader>
          <NetworkConfig
            value={networkConfigValue}
            onChange={handleNetworkChange}
            networks={networksData}
          />
          {errors.network && (
            <div style={{ marginTop: 6, fontSize: 12, color: '#f43f5e' }}>{errors.network}</div>
          )}
        </div>

        {/* Access */}
        <div style={{ marginBottom: 32 }}>
          <SectionHeader>Access</SectionHeader>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <label style={{ fontSize: 12, fontWeight: 500, color: '#94a3b8' }}>
              SSH Public Key
            </label>
            <textarea
              id="ssh-public-key"
              rows={4}
              placeholder="ssh-rsa AAAA... your-key-comment"
              value={form.ssh_public_key}
              onChange={e => setForm(f => ({ ...f, ssh_public_key: e.target.value }))}
              style={{
                width: '100%',
                boxSizing: 'border-box',
                background: '#0a0a0f',
                border: `1px solid ${errors.ssh_public_key ? '#f43f5e' : '#1e1e2e'}`,
                borderRadius: 8,
                color: '#e2e8f0',
                fontSize: 13,
                fontFamily: 'JetBrains Mono, monospace',
                padding: '10px 12px',
                resize: 'vertical',
                outline: 'none',
                transition: 'border-color 150ms',
              }}
              onFocus={e => { e.target.style.borderColor = '#6366f1' }}
              onBlur={e => { e.target.style.borderColor = errors.ssh_public_key ? '#f43f5e' : '#1e1e2e' }}
            />
            {errors.ssh_public_key && (
              <div style={{ fontSize: 12, color: '#f43f5e' }}>{errors.ssh_public_key}</div>
            )}
            <div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigator.clipboard.readText()
                  .then(text => setForm(f => ({ ...f, ssh_public_key: text })))
                  .catch(() => {})}
              >
                Paste from clipboard
              </Button>
            </div>
          </div>
        </div>

        {/* Progress steps */}
        {showProgress && (
          <div style={{
            background: '#111118',
            border: '1px solid #1e1e2e',
            borderRadius: 12,
            padding: 20,
            marginBottom: 16,
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {PROVISION_STEPS.map((step, i) => {
                const isDone = provision.isPending
                  ? i < stepIndex
                  : provisionResult
                    ? true
                    : false
                const isCurrent = provision.isPending && i === stepIndex
                const isError = provision.isError && i === stepIndex
                const isFuture = provision.isPending && i > stepIndex

                return (
                  <div key={step} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ flexShrink: 0, width: 18, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      {isError ? (
                        <XCircle size={16} color="#f43f5e" />
                      ) : isDone ? (
                        <CheckCircle2 size={16} color="#10b981" />
                      ) : isCurrent ? (
                        <Loader2
                          size={16}
                          color="#6366f1"
                          style={{ animation: 'spin 1s linear infinite' }}
                        />
                      ) : (
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#1e1e2e', display: 'inline-block' }} />
                      )}
                    </span>
                    <span style={{
                      fontSize: 13,
                      color: isError ? '#f43f5e' : isDone ? '#10b981' : isCurrent ? '#e2e8f0' : '#64748b',
                      fontWeight: isCurrent ? 500 : 400,
                      transition: 'color 150ms',
                    }}>
                      {step}
                    </span>
                  </div>
                )
              })}
            </div>

            {/* Result */}
            {provisionResult && (
              <div style={{ marginTop: 20, paddingTop: 20, borderTop: '1px solid #1e1e2e' }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: '#10b981', marginBottom: 12 }}>
                  VM Ready!
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, color: '#64748b', minWidth: 80 }}>IP Address</span>
                    <CopyButton text={provisionResult.ip} label={provisionResult.ip} />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, color: '#64748b', minWidth: 80 }}>SSH</span>
                    <CopyButton text={'ssh ubuntu@' + provisionResult.ip} />
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <a
                      href={'/vms/' + form.vm_name}
                      style={{ fontSize: 13, color: '#6366f1', textDecoration: 'none', fontWeight: 500 }}
                    >
                      View VM →
                    </a>
                  </div>
                </div>
              </div>
            )}

            {/* Error message */}
            {provision.isError && (
              <div style={{ marginTop: 12, fontSize: 13, color: '#f43f5e' }}>
                {provision.error?.message || 'Provisioning failed. Check logs for details.'}
              </div>
            )}
          </div>
        )}

        {/* Submit */}
        <Button
          variant="primary"
          size="lg"
          loading={provision.isPending}
          disabled={provision.isPending}
          onClick={handleSubmit}
          style={{ width: '100%' }}
        >
          Provision VM
        </Button>
        {submitted && Object.keys(errors).length > 0 && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#f43f5e' }}>
            Please fix the errors above before submitting.
          </div>
        )}

        {/* Spinner keyframe injected once */}
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>

      {/* ── Right column: Resource Summary ── */}
      <div style={{
        position: 'sticky',
        top: 80,
        background: '#111118',
        border: '1px solid #1e1e2e',
        borderRadius: 12,
        padding: 0,
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid #1e1e2e',
          fontSize: 13,
          fontWeight: 600,
          color: '#94a3b8',
          textTransform: 'uppercase',
          letterSpacing: '0.07em',
        }}>
          Resource Summary
        </div>
        <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <SummaryRow label="VM Name" value={form.vm_name || '—'} />
          <SummaryRow label="OS" value={UBUNTU_LABELS[form.ubuntu_version] || '—'} />
          <SummaryRow label="CPU" value={`${form.cpu} vCPU`} />
          <SummaryRow label="Memory" value={formatRam(form.ram_mb)} />
          <SummaryRow label="Disk" value={`${form.disk_gb} GB`} />
          <SummaryRow
            label="Pool"
            value={selectedPool ? `${selectedPool.name} · ${selectedPool.path}` : '—'}
          />
          <SummaryRow
            label="Network"
            value={selectedNetwork ? selectedNetwork.label : '—'}
          />
          <SummaryRow
            label="IP Mode"
            value={form.ip_mode === 'dhcp' ? 'DHCP' : form.static_ip || 'Static'}
          />
        </div>
      </div>
    </div>
  )
}
