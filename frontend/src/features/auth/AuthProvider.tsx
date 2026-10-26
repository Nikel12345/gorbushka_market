import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authApi, type LoginPayload, type RegisterPayload, type User } from '@/shared/api'
import { AuthContext, type AuthContextValue, type AuthStatus } from './AuthContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')

  const applyUser = useCallback((next: User | null) => {
    setUser(next)
    setStatus(next ? 'authenticated' : 'anonymous')
  }, [])

  const refresh = useCallback(
    () =>
      authApi
        .me()
        .then(applyUser)
        .catch(() => applyUser(null)),
    [applyUser],
  )

  // Восстанавливаем сессию при загрузке приложения
  useEffect(() => {
    void refresh()
  }, [refresh])

  const login = useCallback(
    async (payload: LoginPayload) => {
      const loggedIn = await authApi.login(payload)
      applyUser(loggedIn)
      return loggedIn
    },
    [applyUser],
  )

  const register = useCallback(
    async (payload: RegisterPayload) => {
      const created = await authApi.register(payload)
      applyUser(created)
      return created
    },
    [applyUser],
  )

  const logout = useCallback(async () => {
    await authApi.logout()
    applyUser(null)
  }, [applyUser])

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, login, register, logout, refresh }),
    [user, status, login, register, logout, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
