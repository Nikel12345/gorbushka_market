// Иконки шапки витрины. Цвет — fill из CSS, размер задаётся CSS.

export function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="market-search__icon">
      <path d="M10 3a7 7 0 015.6 11.2l5.1 5.1-1.4 1.4-5.1-5.1A7 7 0 1110 3zm0 2a5 5 0 100 10 5 5 0 000-10z" />
    </svg>
  )
}

export function OrdersIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="market-nav__icon">
      <path d="M12 2l9 4.5v11L12 22l-9-4.5v-11L12 2zm0 2.2L6.3 7 12 9.8 17.7 7 12 4.2zM5 8.6v7.7l6 3V11.6l-6-3zm14 0l-6 3v7.7l6-3V8.6z" />
    </svg>
  )
}

export function CartIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="market-nav__icon">
      <path d="M2 3h3.2l.8 3H21l-2.6 9H7.6L4.6 5H2V3zm6.5 14a2 2 0 110 4 2 2 0 010-4zm9 0a2 2 0 110 4 2 2 0 010-4z" />
    </svg>
  )
}

export function LoginIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="market-nav__icon">
      <path d="M12 12a4.5 4.5 0 100-9 4.5 4.5 0 000 9zm0 2c-4.7 0-8.5 2.4-8.5 5.3V21h17v-1.7c0-2.9-3.8-5.3-8.5-5.3z" />
    </svg>
  )
}

export function StoreIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="market-nav__icon">
      <path d="M20 4H4v2h16V4zm1 10v-2l-1-5H4l-1 5v2h1v6h10v-6h4v6h2v-6h1zm-9 4H6v-4h6v4z" />
    </svg>
  )
}
