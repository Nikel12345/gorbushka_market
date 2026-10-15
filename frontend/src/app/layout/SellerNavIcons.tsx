// Иконки меню кабинета. Цвет — currentColor, размер задаётся CSS.

export function ProductsIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="seller-nav__icon">
      <path
        fillRule="evenodd"
        d="M3 3h8.2l9.8 9.8-8.2 8.2L3 11.2V3zm4.5 2.5a2 2 0 100 4 2 2 0 000-4z"
      />
    </svg>
  )
}

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
