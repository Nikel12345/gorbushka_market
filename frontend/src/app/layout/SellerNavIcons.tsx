// Иконки меню кабинета. Цвет — currentColor, размер задаётся CSS.

export function OrdersIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="seller-nav__icon">
      <path
        fillRule="evenodd"
        d="M5 2h14v20l-2.33-1.5L14.33 22 12 20.5 9.67 22l-2.34-1.5L5 22V2zm3 5v2h8V7H8zm0 4v2h8v-2H8zm0 4v2h5v-2H8z"
      />
    </svg>
  )
}

export function ProfileIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="seller-nav__icon">
      <path d="M12 12a4.5 4.5 0 100-9 4.5 4.5 0 000 9zm0 2c-4.7 0-8.5 2.4-8.5 5.3V21h17v-1.7c0-2.9-3.8-5.3-8.5-5.3z" />
    </svg>
  )
}

export function ShopIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="seller-nav__icon">
      <path d="M4 3h16l1.5 6a3 3 0 01-1.5 2.6V21H4v-9.4A3 3 0 012.5 9L4 3zm2 9.9V19h4v-4h4v4h4v-6.1a3 3 0 01-3-1.3 3 3 0 01-3 1.4 3 3 0 01-3-1.4 3 3 0 01-3 1.3z" />
    </svg>
  )
}

export function AddIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="seller-nav__icon">
      <path d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5z" />
    </svg>
  )
}
