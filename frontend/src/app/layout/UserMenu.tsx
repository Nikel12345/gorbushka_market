import { useId, useRef, useState, type CSSProperties, type ToggleEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '@/features/auth'
import type { User } from '@/shared/api'
import { formatPersonName } from '@/shared/lib'
import { Avatar } from '@/shared/ui'

/** Аватар в шапке и меню под ним. Меню — нативный popover: закрывается кликом мимо и Esc. */
export function UserMenu({ user }: { user: User }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const menuId = useId()
  const buttonRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState<CSSProperties>()
  const name = formatPersonName(user)

  // popover живёт в верхнем слое и не знает о кнопке — ставим его под аватар при открытии,
  // правым краем к правому краю аватара (сдвиг на свою ширину — в CSS)
  function handleBeforeToggle(event: ToggleEvent<HTMLDivElement>) {
    const rect = buttonRef.current?.getBoundingClientRect()
    if (event.newState !== 'open' || !rect) return
    setPosition({ top: rect.bottom + 6, left: rect.right })
  }

  const close = () => menuRef.current?.hidePopover()

  async function handleLogout() {
    close()
    await logout()
    navigate('/', { replace: true })
  }

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className="market-nav__avatar"
        popoverTarget={menuId}
        aria-label="Меню профиля"
        title={user.email}
      >
        <Avatar name={name} size={36} />
      </button>

      <div
        ref={menuRef}
        id={menuId}
        popover="auto"
        className="user-menu"
        style={position}
        onBeforeToggle={handleBeforeToggle}
      >
        <div className="user-menu__head">
          <Avatar name={name} size={40} />
          <div className="user-menu__who">
            <span className="user-menu__name">{name}</span>
            <span className="user-menu__email">{user.email}</span>
          </div>
        </div>
        <Link to="/profile" className="user-menu__item" onClick={close}>
          Профиль
        </Link>
        <Link to="/seller" className="user-menu__item" onClick={close}>
          Кабинет продавца
        </Link>
        <button type="button" className="user-menu__item" onClick={handleLogout}>
          Выйти
        </button>
      </div>
    </>
  )
}
