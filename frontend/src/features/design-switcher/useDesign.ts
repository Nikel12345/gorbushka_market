import { useCallback, useLayoutEffect, useState } from 'react'
import { config } from '@/shared/config'
import { DEFAULT_DESIGN, isDesignId, type DesignId } from './designs'

const STORAGE_KEY = 'design'

function readStoredDesign(): DesignId {
  // Переключатель скрыт — у всех вариант по умолчанию, даже если раньше выбирали другой
  if (!config.designSwitcher) return DEFAULT_DESIGN
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return isDesignId(stored) ? stored : DEFAULT_DESIGN
  } catch {
    return DEFAULT_DESIGN
  }
}

/**
 * Вариант дизайна витрины: ставит data-design на <html>, пока витрина на экране, и помнит выбор
 * в браузере. Админка магазина варианты не наследует — при уходе из витрины атрибут снимается.
 */
export function useDesign() {
  const [design, setDesignState] = useState<DesignId>(readStoredDesign)

  // До отрисовки — чтобы страница не мигнула вариантом по умолчанию
  useLayoutEffect(() => {
    const root = document.documentElement
    root.dataset.design = design
    return () => {
      delete root.dataset.design
    }
  }, [design])

  const setDesign = useCallback((next: DesignId) => {
    setDesignState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Хранилище недоступно (приватный режим) — выбор действует до перезагрузки
    }
  }, [])

  return { design, setDesign }
}
