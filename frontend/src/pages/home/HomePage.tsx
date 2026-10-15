import { useEffect, useState } from 'react'
import { fetchHealth } from '@/shared/api'

type BackendStatus = 'loading' | 'ok' | 'error'

export function HomePage() {
  const [status, setStatus] = useState<BackendStatus>('loading')

  useEffect(() => {
    fetchHealth()
      .then(() => setStatus('ok'))
      .catch(() => setStatus('error'))
  }, [])

  return (
    <main style={{ padding: 24 }}>
      <h1>Gorbushka Market</h1>
      <p>Backend: {status}</p>
    </main>
  )
}
