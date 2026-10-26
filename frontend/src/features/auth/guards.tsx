import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { EmptyState, LinkButton } from '@/shared/ui'
import { useAuth } from './useAuth'

interface RequireAuthProps {
  children: ReactNode
  /** Что показать гостю вместо перехода на вход (например, <LoginRequired />) */
  guest?: ReactNode
}

/** Пускает только авторизованных, остальных отправляет на вход с возвратом обратно. */
export function RequireAuth({ children, guest }: RequireAuthProps) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return null
  if (status === 'anonymous') {
    return guest ?? <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return children
}

/** Экран «Вы не авторизованы» на месте закрытой страницы; после входа — обратно на неё. */
export function LoginRequired({ text }: { text: string }) {
  const location = useLocation()
  return (
    <EmptyState
      title="Вы не авторизованы"
      text={text}
      action={
        <LinkButton variant="primary" to="/login" state={{ from: location.pathname }}>
          Войти
        </LinkButton>
      }
    />
  )
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
