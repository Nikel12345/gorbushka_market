import type { ReactNode } from 'react'
import { store } from '@/shared/config'
import { Card, LinkButton } from '@/shared/ui'
import './AboutPage.css'

/** О магазине: где он, как добраться и как получить заказ. Только справочный текст, без запросов к API. */
export function AboutPage() {
  return (
    <div className="about-page">
      <section className="about-hero">
        <p className="about-hero__eyebrow">О магазине</p>
        <h1 className="about-hero__title">Горбушка на Барклая, 8</h1>
        <p className="about-hero__lead">
          Тот самый торговый центр электроники в Филях. Выбирайте технику на сайте, а забрать её можно в павильоне
          или получить с курьером.
        </p>
        <div className="about-hero__actions">
          <LinkButton to="/" variant="primary">
            Перейти в каталог
          </LinkButton>
          <a className="ui-button ui-button--default" href={store.mapUrl} target="_blank" rel="noreferrer">
            Открыть на карте
          </a>
        </div>
      </section>

      <ul className="about-facts">
        <Fact icon={<PlaceIcon />} label="Адрес" value={store.address} note={store.mall} />
        <Fact icon={<MetroIcon />} label="Метро" value={`«${store.metro}»`} note="Филёвская линия, 5 минут пешком" />
        <Fact icon={<ClockIcon />} label="Часы работы" value={store.hours} note="Ежедневно, без выходных" />
      </ul>

      <div className="about-page__columns">
        <Card title="Как добраться">
          <div className="about-text">
            <p>
              Торговый центр стоит на углу улицы Барклая и Багратионовского проезда. От метро «{store.metro}» —
              около 5 минут пешком.
            </p>
            <p>
              Маршрут на машине или общественном транспорте удобно построить в{' '}
              <a href={store.mapUrl} target="_blank" rel="noreferrer">
                Яндекс Картах
              </a>
              .
            </p>
          </div>
        </Card>

        <Card title="Как получить заказ">
          <dl className="about-delivery">
            <dt>Самовывоз</dt>
            <dd>
              Соберём заказ и будем ждать вас в павильоне магазина. Точный адрес — павильон, ряд и место — покажем
              при оформлении и в карточке заказа.
            </dd>
            <dt>Курьер</dt>
            <dd>Привезём заказ в удобный интервал — выбрать его можно при оформлении.</dd>
          </dl>
        </Card>
      </div>

      <Card title="Почему «Горбушка»">
        <div className="about-text">
          <p>
            Название пошло от ДК имени Горбунова в Филях: в 90-е там работал самый известный в Москве рынок
            кассет, дисков и техники. Потом торговля переехала в отдельный торговый центр на улице Барклая — и
            «Горбушкой» теперь называют его.
          </p>
          <p>Сегодня здесь продают смартфоны, ноутбуки, аудио- и фототехнику, игровые приставки и аксессуары к ним.</p>
        </div>
      </Card>
    </div>
  )
}

function Fact({ icon, label, value, note }: { icon: ReactNode; label: string; value: string; note: string }) {
  return (
    <li className="about-fact">
      {icon}
      <div className="about-fact__text">
        <span className="about-fact__label">{label}</span>
        <span className="about-fact__value">{value}</span>
        <span className="about-fact__note">{note}</span>
      </div>
    </li>
  )
}

// Иконки фактов. Цвет — fill из CSS.

function PlaceIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="about-fact__icon">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z" />
    </svg>
  )
}

function MetroIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="about-fact__icon">
      <path d="M12 2c-4.42 0-8 .5-8 4v9.5C4 17.43 5.57 19 7.5 19L6 20.5v.5h12v-.5L16.5 19c1.93 0 3.5-1.57 3.5-3.5V6c0-3.5-3.58-4-8-4zM7.5 17a1.5 1.5 0 110-3 1.5 1.5 0 010 3zm3.5-6H6V6h5v5zm5.5 6a1.5 1.5 0 110-3 1.5 1.5 0 010 3zm1.5-6h-5V6h5v5z" />
    </svg>
  )
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="about-fact__icon">
      <path d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 18a8 8 0 110-16 8 8 0 010 16zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z" />
    </svg>
  )
}
