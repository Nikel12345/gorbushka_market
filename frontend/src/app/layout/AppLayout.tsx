import { NavLink, Outlet } from 'react-router'
import { useAuth } from '@/features/auth'
import { HeaderSearch } from './HeaderSearch'
import { Logo } from './Logo'
import { CartIcon, LoginIcon, OrdersIcon, SellIcon } from './MarketNavIcons'
import { UserMenu } from './UserMenu'
import './AppLayout.css'

const navLinkClassName = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'market-nav__link market-nav__link--active' : 'market-nav__link'

/** Каркас витрины: шапка с поиском и разделами покупателя. В кабинете продавца — свой каркас. */
export function AppLayout() {
  const { user, status } = useAuth()

  return (
    <div className="market">
      <header className="market-bar">
        <div className="market-bar__inner">
          <Logo />
          <HeaderSearch />
          <nav className="market-nav" aria-label="Разделы">
            <NavLink to="/orders" className={navLinkClassName}>
              <OrdersIcon />
              <span className="market-nav__label">Заказы</span>
            </NavLink>
            <NavLink to="/cart" className={navLinkClassName}>
              <CartIcon />
              <span className="market-nav__label">Корзина</span>
            </NavLink>
            <NavLink to="/seller" className={navLinkClassName}>
              <SellIcon />
              <span className="market-nav__label">Продавать</span>
            </NavLink>

            {status === 'authenticated' && user && <UserMenu user={user} />}
            {status === 'anonymous' && (
              <NavLink to="/login" className={navLinkClassName}>
                <LoginIcon />
                <span className="market-nav__label">Войти</span>
              </NavLink>
            )}
            {/* Пока сессия проверяется — пустое место под аватар, чтобы шапка не прыгала */}
            {status === 'loading' && <span className="market-nav__placeholder" />}
          </nav>
        </div>
      </header>

      <main className="market-main">
        <Outlet />
      </main>
    </div>
  )
}
