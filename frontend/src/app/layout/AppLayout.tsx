import { Link, NavLink, Outlet, ScrollRestoration } from 'react-router'
import { useAuth } from '@/features/auth'
import { useCart } from '@/features/cart'
import { store } from '@/shared/config'
import { HeaderSearch } from './HeaderSearch'
import { Logo } from './Logo'
import { CartIcon, LoginIcon, OrdersIcon, StoreIcon } from './MarketNavIcons'
import { UserMenu } from './UserMenu'
import './AppLayout.css'

const navLinkClassName = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'market-nav__link market-nav__link--active' : 'market-nav__link'

/** Каркас витрины: шапка с поиском и разделами покупателя, подвал с адресом. В админке магазина — свой каркас. */
export function AppLayout() {
  const { user, status } = useAuth()
  const { itemsCount } = useCart()

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
              <span className="market-nav__icon-wrap">
                <CartIcon />
                {itemsCount > 0 && (
                  <span className="market-nav__badge" aria-label={`товаров в корзине: ${itemsCount}`}>
                    {itemsCount > 99 ? '99+' : itemsCount}
                  </span>
                )}
              </span>
              <span className="market-nav__label">Корзина</span>
            </NavLink>
            <NavLink to="/about" className={navLinkClassName}>
              <StoreIcon />
              <span className="market-nav__label">О магазине</span>
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
      <footer className="market-footer">
        <div className="market-footer__inner">
          <span>
            {store.mall}, {store.address} · ежедневно {store.hours}
          </span>
          <Link to="/about" className="market-footer__link">
            О магазине
          </Link>
        </div>
      </footer>
      {/* Новая страница — сверху, «назад» — на прежнее место (лента на главной) */}
      <ScrollRestoration />
    </div>
  )
}
