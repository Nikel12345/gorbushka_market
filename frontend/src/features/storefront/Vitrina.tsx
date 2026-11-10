import type { CSSProperties } from 'react'
import { Link } from 'react-router'
import { store } from '@/shared/config'
import { formatPrice } from '@/shared/lib'
import { useCategories, useHeroProgress, useProductsByIds, usePromoProducts } from './hooks'
import { ArrowIcon, ClockIcon, PinIcon, TruckIcon } from './icons'
import { catalogLink, scrollToCatalog } from './links'
import { Reveal } from './shared'
import { getStoreStatus } from './storeStatus'

/** Товары дуги на первом экране — как в макете; на телефоне видны пять центральных */
const ARC_IDS = [137, 69, 133, 122, 139, 131, 138, 92, 76]
const IPHONE_ID = 122
const AIRPODS_ID = 51
const GPU_ID = 35
/** «Сборка ПК под заказ» — куда ведёт «Собрать ПК» */
const PC_BUILD_ID = 48

/** Плитки категорий: подпись (на телефоне — короче) и фото товара из неё */
const CATEGORY_TILES: { slug: string; name: string; short: string; productId: number; mobileOnly?: boolean }[] = [
  { slug: 'smartfony-i-gadzhety', name: 'Смартфоны и гаджеты', short: 'Смартфоны', productId: 122 },
  { slug: 'audiotekhnika', name: 'Аудиотехника', short: 'Аудио', productId: 133 },
  { slug: 'noutbuki-i-kompyutery', name: 'Ноутбуки и компьютеры', short: 'Ноутбуки и ПК', productId: 131 },
  { slug: 'tv-i-multimedia', name: 'ТВ и мультимедиа', short: 'ТВ', productId: 92 },
  { slug: 'igry-i-konsoli', name: 'Игры и консоли', short: 'Консоли', productId: 139 },
  { slug: 'foto-i-video', name: 'Фото и видео', short: 'Фото и видео', productId: 69 },
  { slug: 'umnyy-dom', name: 'Умный дом', short: 'Умный дом', productId: 87 },
  { slug: 'smart-chasy-i-braslety', name: 'Смарт-часы', short: 'Часы', productId: 138, mobileOnly: true },
]

const PRODUCT_IDS = [...ARC_IDS, AIRPODS_ID, GPU_ID, 87]

/** «Витрина»: первый экран, промо и категории над лентой */
export function VitrinaIntro() {
  const hero = useHeroProgress<HTMLElement>()
  const status = getStoreStatus()
  const { products } = useProductsByIds(PRODUCT_IDS)
  const arc = ARC_IDS.flatMap((id) => {
    const product = products.get(id)
    return product?.image ? [product] : []
  })
  const center = (arc.length - 1) / 2

  return (
    <>
      <section className="sf-vitrina-hero" ref={hero}>
        <div className="sf-wrap sf-vitrina-hero__text">
          <p className="sf-vitrina-hero__status sf-in">
            <span className={status.open ? 'sf-dot sf-dot--open' : 'sf-dot'} />
            {status.text} · Барклая, 8
          </p>
          <h1 className="sf-vitrina-hero__title">
            <span className="sf-in sf-in--1">
              Вся <em>Горбушка</em>
            </span>{' '}
            <span className="sf-in sf-in--2">в одном окне</span>
          </h1>
          <p className="sf-vitrina-hero__lead sf-in sf-in--3">
            <span className="sf-desktop-only">
              Смартфоны, ноутбуки, консоли и аудио от продавцов ТЦ на Барклая, 8. Заберите в павильоне или получите
              курьером за 1–2 дня.
            </span>
            <span className="sf-mobile-only">
              Техника от продавцов ТЦ на Барклая, 8. Самовывоз из павильона или курьер за 1–2 дня.
            </span>
          </p>
          <div className="sf-vitrina-hero__actions sf-in sf-in--4">
            <button type="button" className="sf-btn sf-btn--ink" onClick={scrollToCatalog}>
              Смотреть каталог
              <ArrowIcon />
            </button>
            <Link to="/about" className="sf-text-link">
              Как добраться
              <ArrowIcon />
            </Link>
          </div>
        </div>

        {arc.length > 0 && (
          <div className="sf-arc" aria-hidden="true">
            {arc.map((product, index) => {
              const offset = index - center
              const style = {
                '--i': offset,
                '--d': `${(0.35 + Math.abs(offset) * 0.1).toFixed(2)}s`,
              } as CSSProperties
              return (
                <div key={product.id} className="sf-arc__item" style={style}>
                  <div className="sf-arc__card">
                    <img src={product.image!} alt="" />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      <VitrinaPromos products={products} />
      <VitrinaCategories products={products} />
    </>
  )
}

type ProductsMap = ReturnType<typeof useProductsByIds>['products']

function VitrinaPromos({ products }: { products: ProductsMap }) {
  const iphone = usePromoProducts('iPhone 16', 'smartfony', 1)
  const rtx = usePromoProducts('RTX', 'videokarty', 1)
  if (!iphone.products.length && !rtx.products.length) return null
  const iphoneImage = products.get(IPHONE_ID)?.image ?? iphone.products[0]?.image
  const airpodsImage = products.get(AIRPODS_ID)?.image
  const gpuImage = products.get(GPU_ID)?.image ?? rtx.products[0]?.image

  return (
    <section className="sf-wrap sf-vitrina-promos" aria-label="Сейчас в наличии">
      {iphone.products.length > 0 && (
        <Reveal className="sf-vitrina-promo-wrap sf-vitrina-promo-wrap--wide">
          <Link to={catalogLink('iPhone 16', iphone.categoryId)} className="sf-vitrina-promo sf-vitrina-promo--light">
            <span className="sf-vitrina-promo__text">
              <span className="sf-eyebrow">
                Apple · в наличии<span className="sf-desktop-only"> в павильонах</span>
              </span>
              <span className="sf-vitrina-promo__title">
                iPhone 16 —<br />в наличии
              </span>
              <span className="sf-vitrina-promo__sub">
                От {formatPrice(iphone.products[0].price)}
                <span className="sf-desktop-only"> · 128, 256 и 512 ГБ</span>
              </span>
              <span className="sf-btn sf-btn--ink sf-vitrina-promo__cta">
                Выбрать модель
                <ArrowIcon />
              </span>
            </span>
            <span className="sf-vitrina-promo__art" aria-hidden="true">
              {iphoneImage && <img src={iphoneImage} alt="" />}
              {airpodsImage && <img src={airpodsImage} alt="" />}
            </span>
          </Link>
        </Reveal>
      )}
      {rtx.products.length > 0 && (
        <Reveal className="sf-vitrina-promo-wrap" delay={0.12}>
          <Link to={`/products/${PC_BUILD_ID}`} className="sf-vitrina-promo sf-vitrina-promo--dark">
            <span className="sf-vitrina-promo__text">
              <span className="sf-eyebrow">Комплектующие ПК</span>
              <span className="sf-vitrina-promo__title sf-vitrina-promo__title--sm">Видеокарты RTX</span>
              <span className="sf-vitrina-promo__sub">
                от {formatPrice(rtx.products[0].price)}
                <span className="sf-desktop-only"> · соберём ПК под заказ</span>
              </span>
              {gpuImage && <img className="sf-vitrina-promo__gpu" src={gpuImage} alt="" />}
              <span className="sf-btn sf-btn--white sf-vitrina-promo__cta">
                Собрать ПК
                <ArrowIcon />
              </span>
            </span>
          </Link>
        </Reveal>
      )}
    </section>
  )
}

function VitrinaCategories({ products }: { products: ProductsMap }) {
  const categories = useCategories()
  const tiles = CATEGORY_TILES.flatMap((tile) => {
    const category = categories.find((item) => item.slug === tile.slug)
    return category ? [{ ...tile, id: category.id }] : []
  })
  if (tiles.length === 0) return null

  return (
    <section className="sf-wrap sf-vitrina-cats">
      <div className="sf-vitrina-cats__head">
        <h2 className="sf-section-title">Каталог</h2>
        <button type="button" className="sf-text-link sf-desktop-only" onClick={scrollToCatalog}>
          Все категории
          <ArrowIcon />
        </button>
      </div>
      <ul className="sf-vitrina-cats__grid">
        {tiles.map((tile) => {
          const image = products.get(tile.productId)?.image
          return (
            <li key={tile.slug} className={tile.mobileOnly ? 'sf-mobile-only' : undefined}>
              <Link to={catalogLink(undefined, tile.id)} className="sf-vitrina-cat">
                <span className="sf-vitrina-cat__name">
                  <span className="sf-desktop-only">{tile.name}</span>
                  <span className="sf-mobile-only">{tile.short}</span>
                </span>
                <span className="sf-vitrina-cat__image">{image && <img src={image} alt="" loading="lazy" />}</span>
              </Link>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

/** «Витрина»: блок о магазине под лентой */
export function VitrinaStore() {
  return (
    <section className="sf-vitrina-store">
      <div className="sf-wrap sf-vitrina-store__inner">
        <Reveal className="sf-vitrina-store__text">
          <p className="sf-eyebrow sf-eyebrow--brand">О магазине</p>
          <h2 className="sf-vitrina-store__title">
            Тот самый рынок
            <br />
            электроники в Филях
          </h2>
          <p className="sf-vitrina-store__lead">
            Название пошло от ДК имени Горбунова: в 90-е там работал самый известный в Москве рынок кассет, дисков и
            техники. Сегодня это ТЦ на Барклая, 8 — а его витрина теперь здесь.
          </p>
          <ul className="sf-vitrina-store__facts">
            <li>
              <span className="sf-fact-icon">
                <PinIcon />
              </span>
              <span>
                <b>{store.address}</b>
                <small>{store.mall}</small>
              </span>
            </li>
            <li>
              <span className="sf-fact-icon sf-fact-icon--metro">М</span>
              <span>
                <b>«{store.metro}»</b>
                <small>Филёвская линия, 5 минут пешком</small>
              </span>
            </li>
            <li>
              <span className="sf-fact-icon">
                <ClockIcon />
              </span>
              <span>
                <b>{store.hours}</b>
                <small>Ежедневно, без выходных</small>
              </span>
            </li>
            <li>
              <span className="sf-fact-icon">
                <TruckIcon />
              </span>
              <span>
                <b>Курьер — 50 ₽</b>
                <small>Привезём за 1–2 дня</small>
              </span>
            </li>
          </ul>
        </Reveal>
        <Reveal className="sf-vitrina-store__map" delay={0.12}>
          <span className="sf-map" aria-hidden="true">
            <span className="sf-map__road sf-map__road--1" />
            <span className="sf-map__road sf-map__road--2" />
            <span className="sf-map__road sf-map__road--3" />
            <span className="sf-map__road sf-map__road--4" />
            <span className="sf-map__pin">
              <span className="sf-map__label">Горбушка · Барклая, 8</span>
              <svg viewBox="0 0 24 24" className="sf-map__marker">
                <path d="M12 22s-7.5-6.6-7.5-12.2a7.5 7.5 0 0 1 15 0C19.5 15.4 12 22 12 22z" />
                <circle cx="12" cy="9.8" r="2.6" />
              </svg>
            </span>
          </span>
          <a href={store.mapUrl} target="_blank" rel="noreferrer" className="sf-btn sf-btn--ink sf-vitrina-store__route">
            Построить маршрут
          </a>
        </Reveal>
      </div>
    </section>
  )
}
