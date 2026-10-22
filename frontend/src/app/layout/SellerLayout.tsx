import { useCallback, useMemo, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router'
import { useAuth } from '@/features/auth'
import { SellerContext, type SellerContextValue } from '@/features/seller'
import { adminApi, ApiError, getErrorMessage, type Shop } from '@/shared/api'
import { formatPersonName, useRequest } from '@/shared/lib'
import { Avatar, Button, Card, EmptyState, ErrorState, Loader } from '@/shared/ui'
import { Logo } from './Logo'
import {
  CategoriesIcon,
  CharacteristicsIcon,
  GroupsIcon,
  OrdersIcon,
  ProductsIcon,
  ProfileIcon,
  ShopIcon,
} from './SellerNavIcons'
import './SellerLayout.css'

const loadShop = (signal: AbortSignal) => adminApi.getShop({ signal })

const navLinkClassName = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'seller-nav__link seller-nav__link--active' : 'seller-nav__link'

/** Каркас админки магазина: верхняя панель, меню справа, контент. Шапки витрины здесь нет. */
export function SellerLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const shopRequest = useRequest(loadShop)
  const { mutate } = shopRequest
  const updateShop = useCallback((shop: Shop) => mutate(() => shop), [mutate])

  const contextValue = useMemo<SellerContextValue | null>(
    () => (shopRequest.data ? { shop: shopRequest.data, updateShop } : null),
    [shopRequest.data, updateShop],
  )

  // Меню на телефоне свёрнуто; переход по пункту закрывает его
  const [menuOpen, setMenuOpen] = useState(false)
  const [menuPath, setMenuPath] = useState(location.pathname)
  if (location.pathname !== menuPath) {
    setMenuPath(location.pathname)
    setMenuOpen(false)
  }

  async function handleLogout() {
    await logout()
    navigate('/', { replace: true })
  }

  let content
  if (contextValue) {
    content = (
      <SellerContext.Provider value={contextValue}>
        <Outlet />
      </SellerContext.Provider>
    )
  } else if (shopRequest.status === 'error') {
    // 404 — магазин ещё не заведён: его создают в админке Django
    const noShop = shopRequest.error instanceof ApiError && shopRequest.error.status === 404
    content = (
      <Card>
        {noShop ? (
          <EmptyState
            title="Магазин ещё не заведён"
            text="Создайте его в админке Django — после этого здесь появятся товары и заказы."
          />
        ) : (
          <ErrorState message={getErrorMessage(shopRequest.error)} onRetry={shopRequest.reload} />
        )}
      </Card>
    )
  } else {
    content = <Loader />
  }

  return (
    <div className="seller">
      <header className="seller-bar">
        <Logo />
        <span className="seller-bar__section">Управление магазином</span>
        <span className="seller-bar__spacer" />
        {user && (
          <Link to="/seller/profile" className="seller-bar__user" title={user.email}>
            <Avatar name={formatPersonName(user)} size={32} />
            <span className="seller-bar__email">{user.email}</span>
          </Link>
        )}
        <Button onClick={handleLogout}>Выйти</Button>
      </header>

      <div className="seller-body">
        <nav className={menuOpen ? 'seller-nav seller-nav--open' : 'seller-nav'} aria-label="Разделы админки">
          <button
            type="button"
            className="seller-nav__toggle"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            Меню
            <span aria-hidden="true">{menuOpen ? '▴' : '▾'}</span>
          </button>

          <div className="seller-nav__content">
            <span className="seller-nav__heading">Витрина</span>
            <NavLink to="/seller/products" className={navLinkClassName}>
              <ProductsIcon />
              <span className="seller-nav__text">Товары</span>
            </NavLink>
            <NavLink to="/seller/categories" className={navLinkClassName}>
              <CategoriesIcon />
              <span className="seller-nav__text">Категории</span>
            </NavLink>
            <NavLink to="/seller/characteristics" className={navLinkClassName}>
              <CharacteristicsIcon />
              <span className="seller-nav__text">Характеристики</span>
            </NavLink>
            <NavLink to="/seller/groups" className={navLinkClassName}>
              <GroupsIcon />
              <span className="seller-nav__text">Группы вариантов</span>
            </NavLink>

            <span className="seller-nav__heading">Магазин</span>
            <NavLink to="/seller/orders" className={navLinkClassName}>
              <OrdersIcon />
              <span className="seller-nav__text">Заказы</span>
            </NavLink>
            <NavLink to="/seller/shop" className={navLinkClassName}>
              <ShopIcon />
              <span className="seller-nav__text">Профиль магазина</span>
            </NavLink>

            <hr className="seller-nav__divider" />

            <NavLink to="/seller/profile" className={navLinkClassName}>
              <ProfileIcon />
              <span className="seller-nav__text">Профиль</span>
            </NavLink>
          </div>
        </nav>

        <main className="seller-content">{content}</main>
      </div>
    </div>
  )
}
