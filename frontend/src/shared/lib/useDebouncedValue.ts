import { useEffect, useState } from 'react'

/** Значение, которое догоняет исходное через delay мс после последнего изменения (поиск по мере ввода). */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return debounced
}
