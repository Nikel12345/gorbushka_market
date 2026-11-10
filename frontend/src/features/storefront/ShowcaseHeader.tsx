import { useEffect, useState, useSyncExternalStore, type FormEvent, type ReactNode } from 'react'
import { Link, NavLink, useLocation, useNavigate, useSearchParams } from 'react-router'
import { useAuth } from '@/features/auth'
import { useCart } from '@/features/cart'
import type { ShowcaseDesignId } from '@/features/design-switcher'
import { updateSearchParams } from '@/shared/lib'
import { useCategories, useScrollFlash } from './hooks'
import { BoxIcon, CartIcon, GridIcon, HeartIcon, HomeIcon, MenuIcon, SearchIcon, UserIcon } from './icons'
import { catalogLink } from './links'
import { useNavItems } from './navItems'
import { UtilityBar } from './StorefrontBars'

const MOBILE_QUERY = '(max-width: 720px)'

function subscribeMobile(callback: () => void) {
  const media = window.matchMedia(MOBILE_QUERY)
  media.addEventListener('change', callback)
  return () => media.removeEventListener('change', callback)
}

/** Узкий экран (телефон) — для текстов, которые CSS не поменяет (placeholder) */
function useIsMobile(): boolean {
  return useSyncExternalStore(
    subscribeMobile,
    () => window.matchMedia(MOBILE_QUERY).matches,
    () => false,
  )
}

const PLACEHOLDERS: Record<ShowcaseDesignId, [desktop: string, mobile: string]> = {
  vitrina: ['iPhone 16, PlayStation 5, наушники Sony…', 'Искать на Горбушке'],
  night: ['iPhone 16, PlayStation 5, наушники Sony…', 'Искать на Горбушке'],
  afisha: ['Что ищем на Горбушке? iPhone 16, PS5, Sony XM5…', 'Что ищем на Горбушке?'],
}

/** Поиск в шапке: как HeaderSearch — ищет по ленте через ?q=, на главной сохраняет остальные фильтры */
function ShowcaseSearch({ design }: { design: ShowcaseDesignId }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const isMobile = useIsMobile()
  const onHome = pathname === '/'
  const urlQuery = onHome ? (searchParams.get('q') ?? '') : ''

  const [value, setValue] = useState(urlQuery)
  const [syncedQuery, setSyncedQuery] = useState(urlQuery)
  if (urlQuery !== syncedQuery) {
    setSyncedQuery(urlQuery)
    setValue(urlQuery)
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const q = value.trim()
    const base = onHome ? searchParams : new URLSearchParams()
    const search = updateSearchParams(base, { q, page: null }).toString()
    navigate({ pathname: '/', search: search ? `?${search}` : '' })
  }

  return (
    <form className="sc-search" role="search" onSubmit={handleSubmit}>
      {design !== 'afisha' && <SearchIcon />}
      <input
        className="sc-search__input"
        type="search"
        placeholder={PLACEHOLDERS[design][isMobile ? 1 : 0]}
        aria-label="Поиск товаров"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        maxLength={200}
      />
      <button type="submit" className="sc-search__button" aria-label="Найти">
        {design === 'afisha' && <SearchIcon />}
        <span className="sc-search__button-text">Найти</span>
      </button>
    </form>
  )
}

/** Выпадающий каталог: верхние категории и их подкатегории */
function CatalogMenu({ onClose }: { onClose: () => void }) {
  const categories = useCategories()
  const top = categories.filter((category) => category.depth === 0)

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <>
      <div className="sc-catalog-backdrop" onClick={onClose} aria-hidden="true" />
      <div className="sc-catalog" role="dialog" aria-label="Каталог">
        <div className="sc-catalog__inner">
          <div className="sc-catalog__head">
            <Link to="/" className="sc-catalog__all" onClick={onClose}>
              Все товары
            </Link>
            <button type="button" className="sc-catalog__close" onClick={onClose}>
              Закрыть
            </button>
          </div>
          <div className="sc-catalog__grid">
            {top.map((category) => (
              <section key={category.id} className="sc-catalog__group">
                <Link to={catalogLink(undefined, category.id)} className="sc-catalog__title" onClick={onClose}>
                  {category.name}
                </Link>
                <ul className="sc-catalog__list">
                  {categories
                    .filter((child) => child.parent_id === category.id)
                    .map((child) => (
                      <li key={child.id}>
                        <Link to={catalogLink(undefined, child.id)} onClick={onClose}>
                          {child.name}
                        </Link>
                      </li>
                    ))}
                </ul>
              </section>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}

const navClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'sc-nav__link sc-nav__link--active' : 'sc-nav__link')

function CartBadge({ count }: { count: number }) {
  if (count <= 0) return null
  return (
    <span className="sc-badge" aria-label={`товаров в корзине: ${count}`}>
      {count > 99 ? '99+' : count}
    </span>
  )
}

/**
 * Шапка «витринных» вариантов (как в макетах): строка с адресом («Витрина»), логотип, «Каталог»,
 * поиск, разделы с подписями, полоса категорий; на телефоне — чипсы под поиском и нижнее меню.
 */
export function ShowcaseHeader({
  design,
  logo,
  userMenu,
}: {
  design: ShowcaseDesignId
  /** Логотип-ссылка на главную (app/layout/Logo) */
  logo: ReactNode
  /** Аватар с меню профиля — для вошедшего (app/layout/UserMenu) */
  userMenu: ReactNode
}) {
  const { user, status } = useAuth()
  const { itemsCount } = useCart()
  const { pathname, search } = useLocation()
  const [searchParams] = useSearchParams()
  const onScroll = useScrollFlash<HTMLDivElement>()
  const desktopItems = useNavItems(design, 'desktop')
  const mobileItems = useNavItems(design, 'mobile')

  // Каталог и поиск на телефоне («Ночь») закрываются при переходе на другую страницу
  const [menuAt, setMenuAt] = useState<string | null>(null)
  const [searchAt, setSearchAt] = useState<string | null>(null)
  const here = pathname + search
  const menuOpen = menuAt === here
  const searchOpen = searchAt === here
  const toggleMenu = () => setMenuAt(menuOpen ? null : here)
  const closeMenu = () => setMenuAt(null)

  const currentCategory = pathname === '/' ? Number(searchParams.get('category')) || null : null
  const isCurrent = (categoryId: number | null) => pathname === '/' && currentCategory === categoryId
  const catClass = (accent: boolean, active: boolean) =>
    ['sc-cats__link', accent && 'sc-cats__link--accent', active && 'sc-cats__link--active'].filter(Boolean).join(' ')

  const catalogButton = (
    <button
      type="button"
      className={menuOpen ? 'sc-catalog-button sc-catalog-button--open' : 'sc-catalog-button'}
      aria-expanded={menuOpen}
      onClick={toggleMenu}
    >
      {design === 'vitrina' ? <GridIcon /> : <MenuIcon />}
      Каталог
    </button>
  )

  const profileLink = user ? '/profile' : '/login'

  return (
    <header
      className={['sc-header', `sc-header--${design}`, searchOpen && 'sc-header--search-open'].filter(Boolean).join(' ')}
    >
      {design === 'vitrina' && <UtilityBar />}

      <div className="sc-bar">
        <div className="sc-bar__inner">
          {logo}
          {design !== 'afisha' && catalogButton}
          <ShowcaseSearch design={design} />

          <nav className="sc-nav" aria-label="Разделы">
            <NavLink to="/orders" className={navClass}>
              <BoxIcon />
              <span className="sc-nav__label">Заказы</span>
            </NavLink>
            <NavLink to="/favorites" className={navClass}>
              <HeartIcon />
              <span className="sc-nav__label">Избранное</span>
            </NavLink>
            <NavLink to="/cart" className={navClass}>
              <span className="sc-nav__icon">
                <CartIcon />
                <CartBadge count={itemsCount} />
              </span>
              <span className="sc-nav__label">Корзина</span>
            </NavLink>
            {status === 'authenticated' && userMenu}
            {status === 'anonymous' && (
              <NavLink to="/login" className={navClass}>
                <UserIcon />
                <span className="sc-nav__label">Войти</span>
              </NavLink>
            )}
            {status === 'loading' && <span className="sc-nav__placeholder" />}
          </nav>

          {/* Телефон: вместо разделов — пара иконок (корзина и заказы — в нижнем меню) */}
          <div className="sc-bar__mobile">
            {design === 'night' && (
              <button
                type="button"
                className="sc-icon-button"
                aria-label="Поиск"
                aria-expanded={searchOpen}
                onClick={() => setSearchAt(searchOpen ? null : here)}
              >
                <SearchIcon />
              </button>
            )}
            {design !== 'afisha' && (
              <Link to="/favorites" className="sc-icon-button" aria-label="Избранное">
                <HeartIcon />
              </Link>
            )}
            {design !== 'night' && (
              <Link to={profileLink} className="sc-icon-button" aria-label={user ? 'Профиль' : 'Войти'}>
                <UserIcon />
              </Link>
            )}
          </div>
        </div>
      </div>

      <nav className="sc-cats" aria-label="Категории">
        <div className="sc-cats__inner x-scroll" onScroll={onScroll}>
          {design === 'afisha' && catalogButton}
          {desktopItems.map((item) => (
            <Link
              key={item.label}
              to={item.to}
              className={catClass(item.accent, item.categoryId !== null && isCurrent(item.categoryId))}
              aria-current={item.categoryId !== null && isCurrent(item.categoryId) ? 'page' : undefined}
            >
              {item.label}
            </Link>
          ))}
          {design === 'afisha' && <span className="sc-cats__meta">Барклая, 8 · 10:00–21:00</span>}
        </div>
      </nav>

      {mobileItems.length > 0 && (
        <nav className="sc-chips x-scroll" aria-label="Категории" onScroll={onScroll}>
          {mobileItems.map((item) => (
            <Link key={item.label} to={item.to} className={item.accent ? 'sc-chip sc-chip--accent' : 'sc-chip'}>
              {item.label}
            </Link>
          ))}
        </nav>
      )}

      {menuOpen && <CatalogMenu onClose={closeMenu} />}

      {/* Нижнее меню на телефоне */}
      <nav className="sc-tabbar" aria-label="Основное меню">
        <NavLink to="/" end className={({ isActive }) => (isActive && !menuOpen ? 'sc-tab sc-tab--active' : 'sc-tab')}>
          <HomeIcon />
          Главная
        </NavLink>
        <button type="button" className={menuOpen ? 'sc-tab sc-tab--active' : 'sc-tab'} onClick={toggleMenu}>
          {design === 'vitrina' ? <GridIcon /> : <MenuIcon />}
          Каталог
        </button>
        <NavLink to="/cart" className={({ isActive }) => (isActive ? 'sc-tab sc-tab--active' : 'sc-tab')}>
          <span className="sc-tab__icon">
            <CartIcon />
            <CartBadge count={itemsCount} />
          </span>
          Корзина
        </NavLink>
        <NavLink to="/orders" className={({ isActive }) => (isActive ? 'sc-tab sc-tab--active' : 'sc-tab')}>
          <BoxIcon />
          Заказы
        </NavLink>
        <NavLink to={profileLink} className={({ isActive }) => (isActive ? 'sc-tab sc-tab--active' : 'sc-tab')}>
          <UserIcon />
          Профиль
        </NavLink>
      </nav>
    </header>
  )
}
