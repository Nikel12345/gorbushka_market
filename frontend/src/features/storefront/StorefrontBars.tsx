import { Link } from 'react-router'
import { store } from '@/shared/config'
import { ClockIcon, PinIcon } from './icons'

/** Тонкая строка над шапкой («Витрина»): адрес, часы, разделы для покупателя */
export function UtilityBar() {
  return (
    <div className="market-utility">
      <div className="market-utility__inner">
        <div className="market-utility__group">
          <span className="market-utility__item">
            <PinIcon />
            {store.address} · {store.mall}
          </span>
          <span className="market-utility__item">
            <ClockIcon />
            Ежедневно {store.hours}
          </span>
        </div>
        <nav className="market-utility__group" aria-label="Покупателям">
          <Link to="/about" className="market-utility__link">
            Доставка и самовывоз
          </Link>
          <Link to="/about" className="market-utility__link">
            Гарантия и возврат
          </Link>
        </nav>
      </div>
    </div>
  )
}
