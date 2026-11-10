import { Link } from 'react-router'
import { formatPrice } from '@/shared/lib'
import { useCategories, useHeroProgress, useProductsByIds, usePromoProducts } from './hooks'
import { ArrowIcon } from './icons'
import { catalogLink } from './links'
import { HeroSearch, Reveal } from './shared'

/** Звёзды фона: псевдослучайно, но одинаково при каждой отрисовке */
function makeStars(count: number, seed: number) {
  let state = seed
  const random = () => {
    state = (state * 16807) % 2147483647
    return state / 2147483647
  }
  return Array.from({ length: count }, (_, index) => ({
    x: Math.round(random() * 1440),
    y: Math.round(random() * 840),
    r: +(0.5 + random() * 1.1).toFixed(2),
    fill: index % 9 === 0 ? '#ff8fa8' : index % 7 === 0 ? '#ffd9b0' : '#ffffff',
  }))
}

const STARS = makeStars(72, 20261102)

const QUICK_QUERIES = ['iPhone 16', 'PlayStation 5', 'AirPods Pro 2', 'RTX 4070', 'DJI Mini 4 Pro']

/** Товары под «iPhone 16 — в наличии»: подпись как в макете; «от» — когда моделей несколько */
const STATEMENT_TILES = [
  { id: 120, label: 'iPhone 16 Pro 256 ГБ', from: false },
  { id: 51, label: 'AirPods Pro 2 USB-C', from: false },
  { id: 101, label: 'Apple Watch Series 10', from: true },
]
const IPHONE_ID = 122
const GPU_ID = 35
const DJI_MINI_ID = 76
const DJI_NEO_ID = 77
const PC_BUILD_ID = 48

/** Круги категорий на телефоне */
const MOBILE_CATEGORIES: [label: string, slug: string, productId: number][] = [
  ['Смартфоны', 'smartfony-i-gadzhety', 122],
  ['Аудио', 'audiotekhnika', 133],
  ['Ноутбуки', 'noutbuki-i-kompyutery', 131],
  ['Консоли', 'igry-i-konsoli', 139],
  ['ТВ', 'tv-i-multimedia', 92],
  ['Фото', 'foto-i-video', 69],
]

const PRODUCT_IDS = [
  ...STATEMENT_TILES.map((tile) => tile.id),
  IPHONE_ID,
  GPU_ID,
  DJI_MINI_ID,
  DJI_NEO_ID,
  ...MOBILE_CATEGORIES.map(([, , id]) => id),
]

/** Три силуэта из точек — сменяют друг друга: телефон → ноутбук → наушники */
function ParticleShapes() {
  const layers = (href: string) => (
    <>
      <use href={href} className="sf-night-flow" stroke="#ffffff" strokeWidth="3.4" strokeDasharray="0.01 10" />
      <use
        href={href}
        className="sf-night-flow"
        stroke="#ff4d73"
        strokeWidth="2.2"
        strokeDasharray="0.01 24"
        strokeDashoffset="5"
      />
      <use href={href} stroke="#ffffff" strokeOpacity="0.45" strokeWidth="1.2" strokeDasharray="0.01 4" strokeDashoffset="2" />
    </>
  )

  return (
    <svg className="sf-night-hero__shape" viewBox="0 0 400 400" fill="none" strokeLinecap="round" aria-hidden="true">
      <defs>
        <g id="sf-shape-phone">
          <rect x="128" y="36" width="144" height="328" rx="30" />
          <rect x="174" y="54" width="52" height="14" rx="7" />
          <path d="M124 112v44" />
        </g>
        <g id="sf-shape-laptop">
          <rect x="84" y="96" width="232" height="156" rx="10" />
          <path d="M48 270h304l-22 30H70z" />
          <path d="M176 284h48" />
        </g>
        <g id="sf-shape-headphones">
          <path d="M104 236v-46a96 96 0 0 1 192 0v46" />
          <rect x="86" y="222" width="52" height="96" rx="22" />
          <rect x="262" y="222" width="52" height="96" rx="22" />
        </g>
      </defs>
      <g className="sf-night-shape sf-night-shape--1">{layers('#sf-shape-phone')}</g>
      <g className="sf-night-shape sf-night-shape--2">{layers('#sf-shape-laptop')}</g>
      <g className="sf-night-shape sf-night-shape--3">{layers('#sf-shape-headphones')}</g>
    </svg>
  )
}

type ProductsMap = ReturnType<typeof useProductsByIds>['products']

/** «Ночь»: первый экран со звёздами, промо над лентой */
export function NightIntro() {
  const hero = useHeroProgress<HTMLElement>()
  const { products } = useProductsByIds(PRODUCT_IDS)

  return (
    <>
      <section className="sf-night-hero" ref={hero}>
        <svg
          className="sf-night-hero__stars"
          viewBox="0 0 1440 840"
          preserveAspectRatio="xMidYMid slice"
          aria-hidden="true"
        >
          {STARS.map((star, index) => (
            <circle key={index} cx={star.x} cy={star.y} r={star.r} fill={star.fill} />
          ))}
        </svg>
        <ParticleShapes />
        <h1 className="sf-night-hero__title">
          {/* Снаружи — сдвиг при прокрутке, внутри — анимация появления: так они не мешают друг другу */}
          <span className="sf-night-hero__word sf-night-hero__word--left">
            <span>Горбушка</span>
          </span>{' '}
          <span className="sf-night-hero__word sf-night-hero__word--right">
            <span>онлайн</span>
          </span>
        </h1>
        <div className="sf-night-hero__bottom">
          <p className="sf-night-hero__lead">Тот самый рынок электроники в Филях — теперь в одном окне</p>
          <HeroSearch className="sf-night-search" placeholder="Что ищем? iPhone 16, PS5, Sony XM5…" />
          <nav className="sf-night-hero__chips" aria-label="Популярные запросы">
            {QUICK_QUERIES.map((query) => (
              <Link key={query} to={catalogLink(query)} className="sf-night-chip">
                {query}
              </Link>
            ))}
          </nav>
        </div>
      </section>

      <NightMobileCategories products={products} />
      <NightStatement products={products} />
      <NightCards products={products} />
    </>
  )
}

function NightMobileCategories({ products }: { products: ProductsMap }) {
  const categories = useCategories()
  const items = MOBILE_CATEGORIES.flatMap(([label, slug, productId]) => {
    const category = categories.find((item) => item.slug === slug)
    return category ? [{ label, id: category.id, image: products.get(productId)?.image }] : []
  })
  if (items.length === 0) return null

  return (
    <nav className="sf-night-circles sf-mobile-only" aria-label="Категории">
      {items.map((item) => (
        <Link key={item.id} to={catalogLink(undefined, item.id)} className="sf-night-circle">
          <span className="sf-night-circle__image">{item.image && <img src={item.image} alt="" />}</span>
          {item.label}
        </Link>
      ))}
    </nav>
  )
}

function NightStatement({ products }: { products: ProductsMap }) {
  const iphone = usePromoProducts('iPhone 16', 'smartfony', 1)
  const cheapest = iphone.products[0]
  if (!cheapest) return null
  const iphoneImage = products.get(IPHONE_ID)?.image ?? cheapest.image

  return (
    <section className="sf-wrap sf-night-statement">
      <Reveal className="sf-night-statement__card">
        <p className="sf-eyebrow sf-eyebrow--night">Сейчас в наличии</p>
        <h2 className="sf-night-statement__title">
          iPhone 16 —<br />в наличии
        </h2>
        <p className="sf-night-statement__lead">
          От {formatPrice(cheapest.price)} · 128, 256 и 512 ГБ
          <span className="sf-desktop-only">. Заберите в павильоне на Барклая, 8 или закажите курьера.</span>
        </p>
        {iphoneImage && <img className="sf-night-statement__image sf-mobile-only" src={iphoneImage} alt="" />}
        <Link to={catalogLink('iPhone 16', iphone.categoryId)} className="sf-btn sf-btn--brand">
          Выбрать iPhone
          <ArrowIcon />
        </Link>
      </Reveal>
      <ul className="sf-night-statement__tiles sf-desktop-only">
        {STATEMENT_TILES.map((tile, index) => {
          const product = products.get(tile.id)
          if (!product) return null
          return (
            <li key={tile.id}>
              <Reveal delay={0.1 * index}>
                <Link to={`/products/${product.id}`} className="sf-night-tile">
                  <span className="sf-night-tile__image">
                    {product.image && <img src={product.image} alt="" loading="lazy" />}
                  </span>
                  <span className="sf-night-tile__title">{tile.label}</span>
                  <span className="sf-night-tile__price">
                    {tile.from ? 'от ' : ''}
                    {formatPrice(product.price)}
                  </span>
                </Link>
              </Reveal>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function NightCards({ products }: { products: ProductsMap }) {
  const rtx = usePromoProducts('RTX', 'videokarty', 1)
  const drones = usePromoProducts(undefined, 'kvadrokoptery', 1)
  const gpu = products.get(GPU_ID)
  const mini = products.get(DJI_MINI_ID)
  const neo = products.get(DJI_NEO_ID)

  return (
    <section className="sf-wrap sf-night-cards sf-desktop-only" aria-label="Подборки">
      {rtx.products[0] && (
        <Reveal className="sf-night-card-wrap">
          <Link to={`/products/${PC_BUILD_ID}`} className="sf-night-card">
            <span className="sf-night-card__text">
              <span className="sf-eyebrow sf-eyebrow--muted">Комплектующие ПК</span>
              <span className="sf-night-card__title">Видеокарты RTX</span>
              <span className="sf-night-card__sub">от {formatPrice(rtx.products[0].price)} · соберём ПК под заказ</span>
              <span className="sf-night-card__link">
                Собрать ПК
                <ArrowIcon />
              </span>
            </span>
            {gpu?.image && <img className="sf-night-card__image" src={gpu.image} alt="" loading="lazy" />}
          </Link>
        </Reveal>
      )}
      {(mini || neo) && (
        <Reveal className="sf-night-card-wrap" delay={0.12}>
          <Link to={catalogLink(undefined, drones.categoryId)} className="sf-night-card">
            <span className="sf-night-card__text">
              <span className="sf-eyebrow sf-eyebrow--muted">Фото и видео</span>
              <span className="sf-night-card__title">
                Снимайте
                <br />с высоты
              </span>
              <span className="sf-night-card__sub">
                {[mini && `DJI Mini 4 Pro — ${formatPrice(mini.price)}`, neo && `DJI Neo — ${formatPrice(neo.price)}`]
                  .filter(Boolean)
                  .join(' · ')}
              </span>
              <span className="sf-night-card__link">
                Все квадрокоптеры
                <ArrowIcon />
              </span>
            </span>
            {mini?.image && (
              <img className="sf-night-card__image sf-night-card__image--tilt" src={mini.image} alt="" loading="lazy" />
            )}
          </Link>
        </Reveal>
      )}
    </section>
  )
}
