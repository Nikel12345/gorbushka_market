import { useCallback, useSyncExternalStore } from 'react'

/**
 * Избранное — в браузере (localStorage), без входа: на бэке его пока нет.
 * Общее для всех вкладок: изменение в одной сразу видно в других (событие storage).
 */
const STORAGE_KEY = 'favorites'
const EMPTY: number[] = []

let snapshot: number[] | null = null
const listeners = new Set<() => void>()

function read(): number[] {
  if (snapshot) return snapshot
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    snapshot = Array.isArray(parsed) ? parsed.filter((id): id is number => Number.isInteger(id)) : []
  } catch {
    snapshot = []
  }
  return snapshot
}

function write(ids: number[]) {
  snapshot = ids
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids))
  } catch {
    // Хранилище недоступно (приватный режим) — избранное живёт до перезагрузки
  }
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  const onStorage = (event: StorageEvent) => {
    if (event.key !== STORAGE_KEY) return
    snapshot = null
    listener()
  }
  window.addEventListener('storage', onStorage)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('storage', onStorage)
  }
}

export function useFavorites() {
  const ids = useSyncExternalStore(subscribe, read, () => EMPTY)
  const toggle = useCallback((id: number) => {
    const current = read()
    write(current.includes(id) ? current.filter((item) => item !== id) : [id, ...current])
  }, [])
  return { ids, has: (id: number) => ids.includes(id), toggle }
}
