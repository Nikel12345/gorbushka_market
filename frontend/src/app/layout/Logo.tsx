import { Link } from 'react-router'
import './Logo.css'

/** Логотип — ссылка на главную. Общий для витрины и админки магазина. */
export function Logo() {
  return (
    <Link to="/" className="app-logo" aria-label="Торговый центр «Горбушка» — на главную">
      <span className="app-logo__caption">торговый центр</span>
      <span className="app-logo__name">горбушка</span>
    </Link>
  )
}
