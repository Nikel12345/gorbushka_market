import { Link, Outlet, useNavigate } from 'react-router'
import { useAuth } from '@/features/auth'

export function AppLayout() {
  const { user, status, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/', { replace: true })
  }

  return (
    <>
      <header className="app-header">
        <Link to="/" className="app-logo">
          Gorbushka Market
        </Link>
        <nav className="app-nav">
          {status === 'authenticated' && user && (
            <>
              <Link to="/seller">Кабинет продавца</Link>
              <Link to="/profile">{user.email}</Link>
              <button type="button" onClick={handleLogout}>
                Выйти
              </button>
            </>
          )}
          {status === 'anonymous' && (
            <>
              <Link to="/login">Войти</Link>
              <Link to="/register">Регистрация</Link>
            </>
          )}
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </>
  )
}
