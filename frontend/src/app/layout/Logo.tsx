import { Link } from 'react-router'
import logoUrl from './logo.jpg'
import './Logo.css'

/** Логотип — ссылка на главную. Общий для витрины и админки магазина. */
export function Logo() {
  return (
    <Link to="/" className="app-logo">
      {/* Размеры файла — чтобы место под картинку было до её загрузки */}
      <img src={logoUrl} alt="Горбушка — на главную" width={1280} height={277} className="app-logo__img" />
    </Link>
  )
}
