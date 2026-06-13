export default function StatusDot({ status }) {
  const classMap = {
    running: 'status-dot status-dot-running',
    stopped: 'status-dot status-dot-stopped',
    provisioning: 'status-dot status-dot-provisioning',
    error: 'status-dot status-dot-error',
  }

  return <span className={classMap[status] || 'status-dot status-dot-stopped'} />
}
