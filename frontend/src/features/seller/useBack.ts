import { useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router'

/**
 * Состояние перехода, которое помнит, пришли ли на страницу изнутри админки.
 * Нужно, когда адрес заменяют (новый товар → его страница): у замены свой key,
 * и по нему уже не понять, открыли страницу ссылкой или из списка.
 */
export interface BackState {
  cameFromApp?: boolean
}

/** «Назад»: туда, откуда пришли (список с фильтрами, группа), а если открыли ссылкой — на fallback. */
export function useBack(fallback: string) {
  const navigate = useNavigate()
  const location = useLocation()
  const cameFromApp = (location.state as BackState | null)?.cameFromApp ?? location.key !== 'default'

  const goBack = useCallback(() => {
    if (cameFromApp) navigate(-1)
    else navigate(fallback, { replace: true })
  }, [cameFromApp, fallback, navigate])

  return { cameFromApp, goBack }
}
