import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNotify } from '../contexts/NotificationContext'

async function apiFetch(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.status === 204 ? null : res.json()
}

// Query hooks
export function useHostStats() {
  return useQuery({
    queryKey: ['host-stats'],
    queryFn: () => apiFetch('/host/stats'),
    refetchInterval: 10000,
  })
}

export function useVMs() {
  return useQuery({
    queryKey: ['vms'],
    queryFn: () => apiFetch('/vms'),
    refetchInterval: 5000,
  })
}

export function useVM(name) {
  return useQuery({
    queryKey: ['vm', name],
    queryFn: () => apiFetch(`/vms/${name}`),
    refetchInterval: 5000,
    enabled: !!name,
  })
}

export function useVMStats(name) {
  return useQuery({
    queryKey: ['vm-stats', name],
    queryFn: () => apiFetch(`/vms/${name}/stats`),
    refetchInterval: 3000,
    enabled: !!name,
  })
}

export function useVMSnapshots(name) {
  return useQuery({
    queryKey: ['vm-snapshots', name],
    queryFn: () => apiFetch(`/vms/${name}/snapshots`),
    enabled: !!name,
  })
}

export function useVMConsole(name) {
  return useQuery({
    queryKey: ['vm-console', name],
    queryFn: () => apiFetch(`/vms/${name}/console`),
    enabled: !!name,
  })
}

export function useNetworks() {
  return useQuery({
    queryKey: ['networks'],
    queryFn: () => apiFetch('/networks'),
  })
}

export function usePools() {
  return useQuery({
    queryKey: ['pools'],
    queryFn: () => apiFetch('/pools'),
  })
}

export function useImages() {
  return useQuery({
    queryKey: ['images'],
    queryFn: () => apiFetch('/images'),
  })
}

export function useImageSyncStatus() {
  return useQuery({
    queryKey: ['image-sync-status'],
    queryFn: () => apiFetch('/images/sync/status'),
  })
}

// Mutation hooks
export function useProvisionVM() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: (data) => apiFetch('/vms/provision', { method: 'POST', body: data }),
    onSuccess: () => {
      notify.success('VM provisioned successfully')
      qc.invalidateQueries({ queryKey: ['vms'] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useStartVM() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: ({ name }) => apiFetch(`/vms/${name}/start`, { method: 'POST' }),
    onSuccess: (_, { name }) => {
      notify.success(`VM ${name} started`)
      qc.invalidateQueries({ queryKey: ['vm', name] })
      qc.invalidateQueries({ queryKey: ['vms'] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useStopVM() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: ({ name }) => apiFetch(`/vms/${name}/stop`, { method: 'POST' }),
    onSuccess: (_, { name }) => {
      notify.success(`VM ${name} stopped`)
      qc.invalidateQueries({ queryKey: ['vm', name] })
      qc.invalidateQueries({ queryKey: ['vms'] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useRestartVM() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: ({ name }) => apiFetch(`/vms/${name}/restart`, { method: 'POST' }),
    onSuccess: (_, { name }) => {
      notify.success(`VM ${name} restarted`)
      qc.invalidateQueries({ queryKey: ['vm', name] })
      qc.invalidateQueries({ queryKey: ['vms'] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useDeleteVM() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: ({ name }) => apiFetch(`/vms/${name}`, { method: 'DELETE' }),
    onSuccess: (_, { name }) => {
      notify.success(`VM ${name} deleted`)
      qc.invalidateQueries({ queryKey: ['vms'] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useResizeVM() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: ({ name, ...data }) => apiFetch(`/vms/${name}/resize`, { method: 'PATCH', body: data }),
    onSuccess: (_, { name }) => {
      notify.success(`VM ${name} resized`)
      qc.invalidateQueries({ queryKey: ['vm', name] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useUpdateVMNetwork() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: ({ name, ...data }) => apiFetch(`/vms/${name}/network`, { method: 'PATCH', body: data }),
    onSuccess: (_, { name }) => {
      notify.success(`VM ${name} network updated`)
      qc.invalidateQueries({ queryKey: ['vm', name] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useCreateSnapshot() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: ({ name, ...data }) => apiFetch(`/vms/${name}/snapshots`, { method: 'POST', body: data }),
    onSuccess: (_, { name }) => {
      notify.success('Snapshot created')
      qc.invalidateQueries({ queryKey: ['vm-snapshots', name] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useRestoreSnapshot() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: ({ name, snap }) => apiFetch(`/vms/${name}/snapshots/${snap}/restore`, { method: 'POST' }),
    onSuccess: (_, { name }) => {
      notify.success('Snapshot restored')
      qc.invalidateQueries({ queryKey: ['vm', name] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useDeleteSnapshot() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: ({ name, snap }) => apiFetch(`/vms/${name}/snapshots/${snap}`, { method: 'DELETE' }),
    onSuccess: (_, { name }) => {
      notify.success('Snapshot deleted')
      qc.invalidateQueries({ queryKey: ['vm-snapshots', name] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useSyncImages() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    // Pass a version key ("2004"|"2204"|"2404") to sync one image; omit for all.
    mutationFn: (version) =>
      apiFetch('/images/sync', { method: 'POST', body: version ? { version } : {} }),
    onSuccess: () => {
      notify.success('Image sync started')
      qc.invalidateQueries({ queryKey: ['images'] })
      qc.invalidateQueries({ queryKey: ['image-sync-status'] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useCreatePool() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: (data) => apiFetch('/pools', { method: 'POST', body: data }),
    onSuccess: () => {
      notify.success('Pool created')
      qc.invalidateQueries({ queryKey: ['pools'] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useDeletePool() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: ({ name }) => apiFetch(`/pools/${name}`, { method: 'DELETE' }),
    onSuccess: () => {
      notify.success('Pool deleted')
      qc.invalidateQueries({ queryKey: ['pools'] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function usePatchPool() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: ({ name, ...data }) => apiFetch(`/pools/${name}`, { method: 'PATCH', body: data }),
    onSuccess: () => {
      notify.success('Pool updated')
      qc.invalidateQueries({ queryKey: ['pools'] })
    },
    onError: (err) => notify.error(err.message),
  })
}

export function useSetDefaultPool() {
  const qc = useQueryClient()
  const notify = useNotify()
  return useMutation({
    mutationFn: ({ name }) => apiFetch(`/pools/${name}/default`, { method: 'POST' }),
    onSuccess: () => {
      notify.success('Default pool updated')
      qc.invalidateQueries({ queryKey: ['pools'] })
    },
    onError: (err) => notify.error(err.message),
  })
}
