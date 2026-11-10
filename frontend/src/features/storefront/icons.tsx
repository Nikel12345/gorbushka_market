// Линейные иконки витрины: цвет — currentColor, размер — из CSS.

const stroke = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
} as const

export function ArrowIcon({ className = 'sf-icon' }: { className?: string }) {
  return (
    <svg {...stroke} strokeWidth={2.2} className={className}>
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </svg>
  )
}

export function PinIcon() {
  return (
    <svg {...stroke} className="sf-icon">
      <path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z" />
      <circle cx="12" cy="9.5" r="2.5" />
    </svg>
  )
}

export function ClockIcon() {
  return (
    <svg {...stroke} className="sf-icon">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  )
}

export function TruckIcon() {
  return (
    <svg {...stroke} className="sf-icon">
      <path d="M3 6h11v10H3z" />
      <path d="M14 10h4l3 3v3h-7" />
      <circle cx="7" cy="18" r="1.8" />
      <circle cx="17" cy="18" r="1.8" />
    </svg>
  )
}

export function StoreIcon() {
  return (
    <svg {...stroke} className="sf-icon">
      <path d="M4 10v10h16V10" />
      <path d="M3 4h18l-1.5 6h-15z" />
      <path d="M9 20v-5h6v5" />
    </svg>
  )
}

export function SearchIcon() {
  return (
    <svg {...stroke} strokeWidth={2} className="sf-icon">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  )
}

export function HeartIcon({ filled = false }: { filled?: boolean }) {
  return (
    <svg {...stroke} strokeWidth={2} fill={filled ? 'currentColor' : 'none'} className="sf-icon">
      <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z" />
    </svg>
  )
}

export function GridIcon() {
  return (
    <svg {...stroke} strokeWidth={2} className="sf-icon">
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  )
}

export function MenuIcon() {
  return (
    <svg {...stroke} strokeWidth={2.2} className="sf-icon">
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  )
}

export function BoxIcon() {
  return (
    <svg {...stroke} className="sf-icon">
      <path d="M21 8 12 3 3 8v8l9 5 9-5z" />
      <path d="m3 8 9 5 9-5" />
      <path d="M12 13v8" />
    </svg>
  )
}

export function CartIcon() {
  return (
    <svg {...stroke} className="sf-icon">
      <circle cx="9" cy="20" r="1.5" />
      <circle cx="18" cy="20" r="1.5" />
      <path d="M2 3h3l2.6 12.4a1.5 1.5 0 0 0 1.5 1.1h8.7a1.5 1.5 0 0 0 1.5-1.1L21 7H6" />
    </svg>
  )
}

export function UserIcon() {
  return (
    <svg {...stroke} className="sf-icon">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5" />
    </svg>
  )
}

export function HomeIcon() {
  return (
    <svg {...stroke} strokeWidth={2} className="sf-icon">
      <path d="M3 11 12 4l9 7" />
      <path d="M5 10v10h14V10" />
    </svg>
  )
}

export function SlidersIcon() {
  return (
    <svg {...stroke} strokeWidth={2} className="sf-icon">
      <path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12" />
      <circle cx="16" cy="6" r="2" />
      <circle cx="10" cy="12" r="2" />
      <circle cx="18" cy="18" r="2" />
    </svg>
  )
}

export function ChevronIcon() {
  return (
    <svg {...stroke} strokeWidth={2} className="sf-icon sf-icon--chevron">
      <path d="m6 9 6 6 6-6" />
    </svg>
  )
}

export function CheckIcon() {
  return (
    <svg {...stroke} strokeWidth={2.4} className="sf-icon">
      <path d="m5 12 5 5 9-10" />
    </svg>
  )
}

export function StarIcon({ empty = false }: { empty?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={empty ? 'sc-star sc-star--empty' : 'sc-star'}>
      <path d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z" />
    </svg>
  )
}

/** Иконка верхней категории по её slug; незнакомая категория — сетка */
export function CategoryIcon({ slug }: { slug: string }) {
  switch (slug) {
    case 'smartfony-i-gadzhety':
      return (
        <svg {...stroke} className="sf-cat-icon">
          <rect x="7" y="2.5" width="10" height="19" rx="2.5" />
          <path d="M11 18.5h2" />
        </svg>
      )
    case 'audiotekhnika':
      return (
        <svg {...stroke} className="sf-cat-icon">
          <path d="M4 15v-3a8 8 0 0 1 16 0v3" />
          <rect x="3" y="14" width="4" height="6.5" rx="1.5" />
          <rect x="17" y="14" width="4" height="6.5" rx="1.5" />
        </svg>
      )
    case 'noutbuki-i-kompyutery':
      return (
        <svg {...stroke} className="sf-cat-icon">
          <rect x="4" y="5" width="16" height="11" rx="1.5" />
          <path d="M2 19h20" />
        </svg>
      )
    case 'tv-i-multimedia':
      return (
        <svg {...stroke} className="sf-cat-icon">
          <rect x="3" y="4.5" width="18" height="12.5" rx="1.5" />
          <path d="M8 21h8M12 17v4" />
        </svg>
      )
    case 'igry-i-konsoli':
      return (
        <svg {...stroke} className="sf-cat-icon">
          <path d="M6.5 8.5h11a4 4 0 0 1 3.9 4.9l-.8 3.4a2.3 2.3 0 0 1-4 1L15 16H9l-1.6 1.8a2.3 2.3 0 0 1-4-1l-.8-3.4a4 4 0 0 1 3.9-4.9z" />
          <path d="M8 11.5v3M6.5 13h3" />
          <path d="M15.5 12h.01M17.5 14h.01" strokeWidth={2.6} />
        </svg>
      )
    case 'foto-i-video':
      return (
        <svg {...stroke} className="sf-cat-icon">
          <path d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z" />
          <circle cx="12" cy="13" r="3.5" />
        </svg>
      )
    case 'umnyy-dom':
      return (
        <svg {...stroke} className="sf-cat-icon">
          <path d="M3 11 12 4l9 7" />
          <path d="M5 10v10h14V10" />
          <path d="M10 20v-5h4v5" />
        </svg>
      )
    default:
      return (
        <svg {...stroke} className="sf-cat-icon">
          <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
          <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
          <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
          <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
        </svg>
      )
  }
}
