import type { ReactNode } from 'react'
import { Link } from 'react-router'
import type { ShowcaseDesignId } from '@/features/design-switcher'
import { store } from '@/shared/config'
import { useCategories } from './hooks'
import { catalogLink } from './links'

/** Справочные разделы пока собраны на странице «О магазине» */
const BUYER_LINKS = ['Как заказать', 'Доставка и самовывоз', 'Оплата', 'Гарантия и возврат']
const CATALOG_LINKS: [label: string, slug: string][] = [
  ['Смартфоны', 'smartfony'],
  ['Ноутбуки', 'noutbuki'],
  ['Аудиотехника', 'audiotekhnika'],
  ['Игры и консоли', 'igry-i-konsoli'],
]

function Column({ title, children }: { title: string; children: ReactNode }) {
  return (
    <nav className="sc-footer__col" aria-label={title}>
      <span className="sc-footer__title">{title}</span>
      {children}
    </nav>
  )
}

/** Подвал «витринных» вариантов: адрес, разделы для покупателя, каталог */
export function ShowcaseFooter({ design, logo }: { design: ShowcaseDesignId; logo: ReactNode }) {
  const categories = useCategories()
  const buyerLinks = design === 'vitrina' ? BUYER_LINKS : BUYER_LINKS.slice(1)

  return (
    <footer className={`sc-footer sc-footer--${design}`}>
      <div className="sc-footer__inner">
        <div className="sc-footer__top">
          <div className="sc-footer__brand">
            {logo}
            <p className="sc-footer__address">
              {design === 'vitrina' && (
                <>
                  {store.address}
                  <br />
                  Ежедневно {store.hours}
                </>
              )}
              {design === 'night' && (
                <>
                  {store.address} · {store.mall}
                  <br />
                  м. «{store.metro}» · ежедневно {store.hours}
                </>
              )}
              {design === 'afisha' && (
                <>
                  {store.address} · {store.mall}
                </>
              )}
            </p>
          </div>
          <Column title="Покупателям">
            {buyerLinks.map((label) => (
              <Link key={label} to="/about">
                {label}
              </Link>
            ))}
          </Column>
          {design === 'vitrina' && (
            <Column title="Каталог">
              {CATALOG_LINKS.map(([label, slug]) => {
                const category = categories.find((item) => item.slug === slug)
                return (
                  <Link key={slug} to={category ? catalogLink(undefined, category.id) : '/'}>
                    {label}
                  </Link>
                )
              })}
            </Column>
          )}
          <Column title="Горбушка">
            <Link to="/about">О магазине</Link>
            <Link to="/about">Контакты</Link>
          </Column>
        </div>
        <div className="sc-footer__bottom">
          <span>© 2026 Горбушка</span>
        </div>
      </div>
    </footer>
  )
}
