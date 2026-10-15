import { Link } from 'react-router'
import './Logo.css'

/** Логотип — ссылка на главную. Общий для витрины и кабинета продавца. */
export function Logo() {
  return (
    <Link to="/" className="app-logo" aria-label="Gorbushka Market — на главную">
      <span className="app-logo__mark" aria-hidden="true">
        G
      </span>
      <span className="app-logo__text">
        Gorbushka<span className="app-logo__light">Market</span>
      </span>
    </Link>
  )
}
