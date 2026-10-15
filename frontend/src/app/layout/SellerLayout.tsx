import { useCallback, useMemo, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useMatch, useNavigate } from 'react-router'
import { useAuth } from '@/features/auth'
import { SellerContext, type SellerContextValue } from '@/features/seller'
import { getErrorMessage, sellerApi, type Shop } from '@/shared/api'
import { formatPersonName, useRequest } from '@/shared/lib'
import { Avatar, Button, Card, ErrorState, Loader } from '@/shared/ui'
import { Logo } from './Logo'
import { AddIcon, OrdersIcon, ProfileIcon, ShopIcon } from './SellerNavIcons'
import './SellerLayout.css'

const loadShops = (signal: AbortSignal) => sellerApi.listShops({ signal })

const navLinkClassName = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'seller-nav__link seller-nav__link--active' : 'seller-nav__link'

const subLinkClassName = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'seller-nav__sub-link seller-nav__sub-link--active' : 'seller-nav__sub-link'

/** Каркас кабинета продавца: верхняя панель, меню справа, контент. Шапки витрины здесь нет. */
export function SellerLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const shopMatch = useMatch('/seller/shops/:shopId/*')

  const shopsRequest = useRequest(loadShops)
  const { mutate } = shopsRequest
  const shops = useMemo(() => shopsRequest.data ?? [], [shopsRequest.data])

  // Запоминаем последний открытый магазин: по нему /seller и заказы выбирают магазин по умолчанию
  const urlShopId = shopMatch ? Number(shopMatch.params.shopId) : null
  const [lastShopId, setLastShopId] = useState<number | null>(null)
  if (urlShopId !== null && !Number.isNaN(urlShopId) && urlShopId !== lastShopId) {
    setLastShopId(urlShopId)
  }
  const activeShopId = shops.some((shop) => shop.id === lastShopId) ? lastShopId : (shops[0]?.id ?? null)

  const addShop = useCallback((shop: Shop) => mutate((data) => [...data, shop]), [mutate])
  const updateShop = useCallback(
    (shop: Shop) => mutate((data) => data.map((item) => (item.id === shop.id ? shop : item))),
    [mutate],
  )

  const contextValue = useMemo<SellerContextValue | null>(
    () => (shopsRequest.data ? { shops, activeShopId, addShop, updateShop } : null),
    [shopsRequest.data, shops, activeShopId, addShop, updateShop],
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
  } else if (shopsRequest.status === 'error') {
    content = (
      <Card>
        <ErrorState message={getErrorMessage(shopsRequest.error)} onRetry={shopsRequest.reload} />
      </Card>
    )
  } else {
    content = <Loader />
  }

  return (
    <div className="seller">
      <header className="seller-bar">
        <Logo />
        <span className="seller-bar__section">Кабинет продавца</span>
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
        <nav className={menuOpen ? 'seller-nav seller-nav--open' : 'seller-nav'} aria-label="Разделы кабинета">
          <button
            type="button"
            className="seller-nav__toggle"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            Меню кабинета
            <span aria-hidden="true">{menuOpen ? '▴' : '▾'}</span>
          </button>

          <div className="seller-nav__content">
            <p className="seller-nav__heading">Магазины</p>
            {shops.map((shop) => (
              <div key={shop.id} className="seller-nav__shop">
                <NavLink
                  to={`/seller/shops/${shop.id}/products`}
                  className={() =>
                    shop.id === urlShopId ? 'seller-nav__link seller-nav__link--current' : 'seller-nav__link'
                  }
                  title={shop.name}
                >
                  <ShopIcon />
                  <span className="seller-nav__text">{shop.name}</span>
                </NavLink>
                <ul className="seller-nav__sub">
                  <li>
                    <NavLink to={`/seller/shops/${shop.id}/products`} className={subLinkClassName}>
                      Товары
                    </NavLink>
                  </li>
                  <li>
                    <NavLink to={`/seller/shops/${shop.id}/profile`} className={subLinkClassName}>
                      Профиль магазина
                    </NavLink>
                  </li>
                </ul>
              </div>
            ))}
            <NavLink to="/seller/shops/new" className={navLinkClassName}>
              <AddIcon />
              <span className="seller-nav__text">Добавить магазин</span>
            </NavLink>

            <hr className="seller-nav__divider" />

            <NavLink to="/seller/orders" className={navLinkClassName}>
              <OrdersIcon />
              <span className="seller-nav__text">Заказы</span>
            </NavLink>
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
