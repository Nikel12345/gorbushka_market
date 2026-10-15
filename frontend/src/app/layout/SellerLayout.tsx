import { useCallback, useMemo, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useMatch, useNavigate } from 'react-router'
import { useAuth } from '@/features/auth'
import { SellerContext, type SellerContextValue } from '@/features/seller'
import { getErrorMessage, sellerApi, type ShopBrief } from '@/shared/api'
import { formatPersonName, useRequest } from '@/shared/lib'
import { Avatar, Button, Card, ErrorState, Loader } from '@/shared/ui'
import { Logo } from './Logo'
import { OrdersIcon, ProductsIcon, ProfileIcon } from './SellerNavIcons'
import './SellerLayout.css'

const loadProfile = (signal: AbortSignal) => sellerApi.profile({ signal })

const navLinkClassName = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'seller-nav__link seller-nav__link--active' : 'seller-nav__link'

/** Каркас кабинета продавца: верхняя панель, меню справа, контент. Шапки витрины здесь нет. */
export function SellerLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const shopMatch = useMatch('/seller/shops/:shopId/*')

  const profile = useRequest(loadProfile)
  const { mutate } = profile
  const shops = profile.data?.shops ?? []

  // Запоминаем последний открытый магазин, чтобы меню вело в него и со страницы профиля
  const urlShopId = shopMatch ? Number(shopMatch.params.shopId) : null
  const [lastShopId, setLastShopId] = useState<number | null>(null)
  if (urlShopId !== null && urlShopId !== lastShopId) {
    setLastShopId(urlShopId)
  }
  const activeShopId = shops.some((shop) => shop.id === lastShopId) ? lastShopId : (shops[0]?.id ?? null)

  const addShop = useCallback(
    (shop: ShopBrief) => mutate((data) => ({ ...data, shops: [...data.shops, shop] })),
    [mutate],
  )

  const contextValue = useMemo<SellerContextValue | null>(
    () => (profile.data ? { profile: profile.data, activeShopId, addShop } : null),
    [profile.data, activeShopId, addShop],
  )

  async function handleLogout() {
    await logout()
    navigate('/', { replace: true })
  }

  function handleShopChange(shopId: string) {
    const section = location.pathname.includes('/orders') ? 'orders' : 'products'
    navigate(`/seller/shops/${shopId}/${section}`)
  }

  let content
  if (contextValue) {
    content = (
      <SellerContext.Provider value={contextValue}>
        <Outlet />
      </SellerContext.Provider>
    )
  } else if (profile.status === 'error') {
    content = (
      <Card>
        <ErrorState message={getErrorMessage(profile.error)} onRetry={profile.reload} />
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

        {shops.length > 1 && (
          <select
            className="seller-bar__shop"
            aria-label="Магазин"
            value={activeShopId ?? ''}
            onChange={(event) => handleShopChange(event.target.value)}
          >
            {shops.map((shop) => (
              <option key={shop.id} value={shop.id}>
                {shop.name}
              </option>
            ))}
          </select>
        )}
        {shops.length === 1 && <span className="seller-bar__shop-name">{shops[0].name}</span>}

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
        <nav className="seller-nav" aria-label="Разделы кабинета">
          {activeShopId !== null && (
            <>
              <NavLink to={`/seller/shops/${activeShopId}/products`} className={navLinkClassName}>
                <ProductsIcon />
                Товары
              </NavLink>
              <NavLink to={`/seller/shops/${activeShopId}/orders`} className={navLinkClassName}>
                <OrdersIcon />
                Заказы
              </NavLink>
            </>
          )}
          <NavLink to="/seller/profile" className={navLinkClassName}>
            <ProfileIcon />
            Профиль
          </NavLink>
        </nav>

        <main className="seller-content">{content}</main>
      </div>
    </div>
  )
}
