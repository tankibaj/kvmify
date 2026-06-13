import { createContext, useContext, useState, useCallback, useRef } from 'react'

const NotificationContext = createContext(null)

export function NotificationProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const notify = useCallback((variant, message) => {
    const id = ++idRef.current
    setToasts(prev => [...prev, { id, variant, message }])
    setTimeout(() => dismiss(id), 4000)
    return id
  }, [dismiss])

  const api = {
    success: (msg) => notify('success', msg),
    error: (msg) => notify('error', msg),
    info: (msg) => notify('info', msg),
    warning: (msg) => notify('warning', msg),
    dismiss,
  }

  return (
    <NotificationContext.Provider value={{ toasts, ...api }}>
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotify() {
  const ctx = useContext(NotificationContext)
  if (!ctx) throw new Error('useNotify must be used within NotificationProvider')
  return ctx
}
