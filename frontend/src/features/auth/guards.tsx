import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { useAuth } from './useAuth'

/** Пускает только авторизованных, остальных отправляет на вход с возвратом обратно. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return null
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return children
}

/** Админка магазина: только сотрудники (is_staff). Гостей — на вход, остальных — на главную. */
export function RequireStaff({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  return <RequireAuth>{user?.is_staff ? children : <Navigate to="/" replace />}</RequireAuth>
}

/**
 * Страницы входа/регистрации: авторизованного пользователя уводим туда,
 * откуда его отправил RequireAuth, иначе на главную. Срабатывает и сразу после
 * входа (статус меняется раньше, чем LoginPage успевает сделать navigate).
 */
export function GuestOnly({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return null
  if (status === 'authenticated') {
    const from = (location.state as { from?: string } | null)?.from ?? '/'
    return <Navigate to={from} replace />
  }
  return children
}
