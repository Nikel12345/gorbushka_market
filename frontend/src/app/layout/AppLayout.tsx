import { Link, NavLink, Outlet, ScrollRestoration, useLocation, useSearchParams } from 'react-router'
import { useAuth } from '@/features/auth'
import { useCart } from '@/features/cart'
import { DesignContext, DesignSwitcher, isShowcaseDesign, useDesign } from '@/features/design-switcher'
import {
  hasCatalogFilters,
  ShowcaseFooter,
  ShowcaseHeader,
  StorefrontIntro,
  StorefrontOutro,
  usePageScrollFlash,
} from '@/features/storefront'
import { config, store } from '@/shared/config'
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
  const { design, setDesign } = useDesign()
  const { pathname } = useLocation()
  const [searchParams] = useSearchParams()

  // «Витринные» варианты (как в макетах): своя шапка и подвал, а на главной без фильтров —
  // первый экран и промо над лентой, блок о магазине под ней
  const showcase = isShowcaseDesign(design) ? design : null
  const landing = showcase !== null && pathname === '/' && !hasCatalogFilters(searchParams)
  // В них полосы прокрутки видны, только пока страницу листают
  usePageScrollFlash(showcase !== null)

  const header = showcase ? (
    <ShowcaseHeader design={showcase} logo={<Logo />} userMenu={user && <UserMenu user={user} />} />
  ) : (
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
  )

  const footer = showcase ? (
    <ShowcaseFooter design={showcase} logo={<Logo />} />
  ) : (
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
  )

  return (
    <DesignContext.Provider value={design}>
      <div className={showcase ? 'market market--showcase' : 'market'}>
        {header}
        {config.designSwitcher && <DesignSwitcher value={design} onChange={setDesign} />}

        {landing && showcase && <StorefrontIntro design={showcase} />}
        {/* id — сюда ведут кнопки «Смотреть каталог» с первого экрана */}
        <main className="market-main" id="catalog">
          <Outlet />
        </main>
        {landing && showcase && <StorefrontOutro design={showcase} />}
        {footer}
        {/* Новая страница — сверху, «назад» — на прежнее место (лента на главной) */}
        <ScrollRestoration />
      </div>
    </DesignContext.Provider>
  )
}
