import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { store } from '@/shared/config'
import { formatPrice } from '@/shared/lib'
import { useProductsByIds, usePromoProducts } from './hooks'
import { ArrowIcon } from './icons'
import { catalogLink, scrollToCatalog } from './links'
import { Reveal } from './shared'

const PS5_ID = 139
const IPHONE_ID = 122
const HEADPHONES_ID = 133
const GPU_ID = 35
const DJI_MINI_ID = 76
const PC_BUILD_ID = 48
const PRODUCT_IDS = [PS5_ID, IPHONE_ID, HEADPHONES_ID, GPU_ID, DJI_MINI_ID]

const MARQUEE = [
  'Смартфоны',
  'Ноутбуки',
  'Наушники',
  'Приставки',
  'Телевизоры',
  'Фотоаппараты',
  'Квадрокоптеры',
  'Видеокарты',
  'Умный дом',
]

/** «Афиша»: плакатный первый экран, бегущая строка и промо над лентой */
export function AfishaIntro() {
  const { products } = useProductsByIds(PRODUCT_IDS)
  const ps5 = products.get(PS5_ID)
  const iphone = products.get(IPHONE_ID)
  const headphones = products.get(HEADPHONES_ID)

  return (
    <>
      <section className="sf-afisha-hero">
        <div className="sf-wrap">
          <h1 className="sf-afisha-hero__title">
            <span className="sf-line">
              <span>Тот самый</span>
            </span>{' '}
            <span className="sf-line sf-line--2">
              <span>рынок техники</span>
            </span>
          </h1>
          <div className="sf-afisha-hero__row">
            <div className="sf-afisha-hero__text">
              <p className="sf-afisha-hero__lead">
                <span className="sf-desktop-only">
                  Смартфоны, ноутбуки, консоли и аудио от павильонов ТЦ на Барклая, 8. Самовывоз из павильона или
                  курьер за 1–2 дня.
                </span>
                <span className="sf-mobile-only">
                  Техника от павильонов ТЦ на Барклая, 8. Самовывоз или курьер за 1–2 дня.
                </span>
              </p>
              <div className="sf-afisha-hero__actions">
                <button type="button" className="sf-hard sf-hard--white" onClick={scrollToCatalog}>
                  В каталог
                  <ArrowIcon />
                </button>
                <Link to="/about" className="sf-hard sf-hard--outline sf-desktop-only">
                  Как добраться
                </Link>
              </div>
            </div>
            <div className="sf-afisha-hero__stickers" aria-hidden="true">
              {ps5?.image && (
                <div className="sf-sticker sf-sticker--1">
                  <div className="sf-sticker__card">
                    <img src={ps5.image} alt="" />
                    <span className="sf-sticker__price">{formatPrice(ps5.price)}</span>
                  </div>
                </div>
              )}
              {iphone?.image && (
                <div className="sf-sticker sf-sticker--2">
                  <div className="sf-sticker__card">
                    <img src={iphone.image} alt="" />
                    <span className="sf-sticker__price">iPhone 16 в наличии</span>
                  </div>
                </div>
              )}
              {headphones?.image && (
                <div className="sf-sticker sf-sticker--3">
                  <div className="sf-sticker__card">
                    <img src={headphones.image} alt="" />
                    <span className="sf-sticker__price">{formatPrice(headphones.price)}</span>
                  </div>
                </div>
              )}
              <div className="sf-sticker sf-sticker--note">
                <div className="sf-sticker__note">
                  Ежедневно
                  <br />
                  {store.hours}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="sf-marquee" aria-hidden="true">
        <div className="sf-marquee__track">
          {/* Две одинаковые половины: лента сдвигается на половину и незаметно начинается заново.
              В каждой половине список дважды — чтобы хватило на широкий экран */}
          {[0, 1].map((copy) => (
            <span key={copy} className="sf-marquee__group">
              {[...MARQUEE, ...MARQUEE].map((label, index) => (
                <span key={index} className="sf-marquee__item">
                  {label}
                  <span className="sf-marquee__dot" />
                </span>
              ))}
            </span>
          ))}
        </div>
      </div>

      <AfishaPromos images={{ iphone: iphone?.image, gpu: products.get(GPU_ID)?.image, drone: products.get(DJI_MINI_ID) }} />
    </>
  )
}

function AfishaPromo({
  tone,
  tag,
  title,
  sub,
  to,
  linkText,
  image,
  delay,
  className,
}: {
  tone: 'white' | 'brand' | 'ink'
  tag: string
  title: ReactNode
  sub: ReactNode
  to: string
  linkText: string
  image: string | null | undefined
  delay?: number
  className?: string
}) {
  return (
    <Reveal className={className ? `sf-afisha-promo-wrap ${className}` : 'sf-afisha-promo-wrap'} delay={delay}>
      <Link to={to} className={`sf-afisha-promo sf-afisha-promo--${tone}`}>
        <span className="sf-afisha-promo__tag">{tag}</span>
        <span className="sf-afisha-promo__title">{title}</span>
        <span className="sf-afisha-promo__sub">{sub}</span>
        <span className="sf-afisha-promo__link">
          {linkText}
          <ArrowIcon />
        </span>
        {image && <img className="sf-afisha-promo__image" src={image} alt="" loading="lazy" />}
      </Link>
    </Reveal>
  )
}

function AfishaPromos({
  images,
}: {
  images: { iphone?: string | null; gpu?: string | null; drone?: { image: string | null; price: string } }
}) {
  const iphone = usePromoProducts('iPhone 16', 'smartfony', 1)
  const rtx = usePromoProducts('RTX', 'videokarty', 1)
  const drones = usePromoProducts(undefined, 'kvadrokoptery', 1)

  return (
    <section className="sf-wrap sf-afisha-promos">
      <h2 className="sf-afisha-title">Сейчас на полках</h2>
      <div className="sf-afisha-promos__grid">
        {iphone.products[0] && (
          <AfishaPromo
            tone="white"
            tag="Apple"
            title={
              <>
                iPhone 16 —<br />в наличии
              </>
            }
            sub={
              <>
                От {formatPrice(iphone.products[0].price)}
                <span className="sf-desktop-only"> · 128, 256 и 512 ГБ</span>
              </>
            }
            to={catalogLink('iPhone 16', iphone.categoryId)}
            linkText="Выбрать модель"
            image={images.iphone ?? iphone.products[0].image}
          />
        )}
        {rtx.products[0] && (
          <AfishaPromo
            tone="brand"
            tag="Комплектующие"
            title={
              <>
                Видеокарты
                <br />
                RTX
              </>
            }
            sub={
              <>
                от {formatPrice(rtx.products[0].price)}
                <span className="sf-desktop-only"> · соберём ПК под заказ</span>
              </>
            }
            to={`/products/${PC_BUILD_ID}`}
            linkText="Собрать ПК"
            image={images.gpu ?? rtx.products[0].image}
            delay={0.1}
          />
        )}
        {images.drone && (
          <AfishaPromo
            tone="ink"
            tag="Фото и видео"
            title={
              <>
                Снимайте
                <br />с высоты
              </>
            }
            sub={`DJI Mini 4 Pro — ${formatPrice(images.drone.price)}`}
            to={catalogLink(undefined, drones.categoryId)}
            linkText="Все квадрокоптеры"
            image={images.drone.image}
            delay={0.2}
            className="sf-desktop-only"
          />
        )}
      </div>
    </section>
  )
}

/** «Афиша»: чёрный блок о магазине под лентой */
export function AfishaStore() {
  return (
    <section className="sf-afisha-store">
      <div className="sf-wrap">
        <Reveal>
          <p className="sf-afisha-store__eyebrow">С 90-х — от ДК Горбунова до ТЦ на Барклая</p>
          <h2 className="sf-afisha-store__title">Барклая, 8</h2>
        </Reveal>
        <dl className="sf-afisha-store__facts">
          <div>
            <dt>Метро</dt>
            <dd>
              <b>«{store.metro}»</b>
              Филёвская линия, 5 минут пешком
            </dd>
          </div>
          <div>
            <dt>Часы работы</dt>
            <dd>
              <b>{store.hours}</b>
              Ежедневно, без выходных
            </dd>
          </div>
          <div>
            <dt>Самовывоз</dt>
            <dd>
              <b>Из павильона продавца</b>
              Ряд и место покажем в заказе
            </dd>
          </div>
          <div>
            <dt>Курьер</dt>
            <dd>
              <b>50 ₽ · 1–2 дня</b>
              Интервал на выбор
            </dd>
          </div>
        </dl>
        <a href={store.mapUrl} target="_blank" rel="noreferrer" className="sf-hard sf-hard--white sf-hard--brand-shadow">
          Построить маршрут
          <ArrowIcon />
        </a>
      </div>
    </section>
  )
}
