import { useState } from 'react'
import { Modal, Button, Input } from '../../components/ui'

export default function CreatePoolModal({ isOpen, onClose, onCreate }) {
  const [name, setName] = useState('')
  const [path, setPath] = useState('')
  const [nameError, setNameError] = useState('')
  const [pathError, setPathError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const validate = () => {
    let valid = true
    if (!name.trim()) { setNameError('Name is required'); valid = false }
    else if (!/^[a-z0-9-]+$/.test(name)) { setNameError('Only lowercase letters, numbers, hyphens'); valid = false }
    else setNameError('')
    if (!path.trim()) { setPathError('Path is required'); valid = false }
    else if (!path.startsWith('/')) { setPathError('Must be an absolute path starting with /'); valid = false }
    else setPathError('')
    return valid
  }

  const handleSubmit = async () => {
    if (!validate()) return
    setSubmitting(true)
    try {
      await onCreate({ name, path })
      setName('')
      setPath('')
      onClose()
    } finally {
      setSubmitting(false)
    }
  }

  const handleClose = () => {
    setName('')
    setPath('')
    setNameError('')
    setPathError('')
    onClose()
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Create Storage Pool"
      footer={
        <>
          <Button variant="ghost" onClick={handleClose} disabled={submitting}>Cancel</Button>
          <Button variant="primary" onClick={handleSubmit} loading={submitting}>Create Pool</Button>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <Input
          label="Pool Name"
          id="pool-name"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="e.g. vm-storage"
          error={nameError}
        />
        <Input
          label="Target Path"
          id="pool-path"
          value={path}
          onChange={e => setPath(e.target.value)}
          placeholder="/var/lib/libvirt/images/mypool"
          error={pathError}
          style={{ fontFamily: 'JetBrains Mono, monospace' }}
        />
        <p style={{ margin: 0, fontSize: '12px', color: '#475569', lineHeight: 1.5 }}>
          The directory will be created on the host if it does not exist. Pool type is always <code style={{ fontFamily: 'JetBrains Mono, monospace', color: '#94a3b8' }}>dir</code>.
        </p>
      </div>
    </Modal>
  )
}
