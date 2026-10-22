import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { promoApi, type Promo } from '@/shared/api'
import { useRequest } from '@/shared/lib'

const loadPromo = (signal: AbortSignal) => promoApi.feed({ signal })

/**
 * Рекламная полоса во всю ширину сетки ленты (~10:1). Каждая полоса запрашивает
 * свою случайную рекламу; нет рекламы или ошибка — полосы нет.
 */
export function FeedPromo() {
  const promo = useRequest(loadPromo)
  const p = promo.data
  if (!p?.image) return null

  const picture = (
    <picture>
      {p.image_mobile && <source media="(max-width: 600px)" srcSet={p.image_mobile} />}
      <img
        src={p.image}
        alt={p.title}
        className={p.image_mobile ? 'feed-promo__image feed-promo__image--has-mobile' : 'feed-promo__image'}
        loading="lazy"
      />
    </picture>
  )

  return (
    <li className="feed-promo">
      <PromoLink promo={p}>
        {picture}
        <span className="feed-promo__label">Реклама</span>
      </PromoLink>
    </li>
  )
}

/** Путь на сайте — Link; внешний адрес — новая вкладка; пусто — без ссылки */
function PromoLink({ promo, children }: { promo: Promo; children: ReactNode }) {
  if (promo.url.startsWith('/')) {
    return (
      <Link to={promo.url} className="feed-promo__link">
        {children}
      </Link>
    )
  }
  if (promo.url) {
    return (
      <a href={promo.url} target="_blank" rel="noopener noreferrer sponsored" className="feed-promo__link">
        {children}
      </a>
    )
  }
  return <div className="feed-promo__link">{children}</div>
}
