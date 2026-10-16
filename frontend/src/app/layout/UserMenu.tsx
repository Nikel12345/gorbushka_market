import { useId, useRef, useState, type CSSProperties, type ToggleEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '@/features/auth'
import { walletApi, type Balance, type User } from '@/shared/api'
import { formatPersonName, formatPrice } from '@/shared/lib'
import { Avatar } from '@/shared/ui'

/** Аватар в шапке и меню под ним. Меню — нативный popover: закрывается кликом мимо и Esc. */
export function UserMenu({ user }: { user: User }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const menuId = useId()
  const buttonRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState<CSSProperties>()
  /** undefined — ещё не загружен, null — не удалось */
  const [balance, setBalance] = useState<Balance | null>()
  const name = formatPersonName(user)

  // popover живёт в верхнем слое и не знает о кнопке — ставим его под аватар при открытии,
  // правым краем к правому краю аватара (сдвиг на свою ширину — в CSS)
  function handleBeforeToggle(event: ToggleEvent<HTMLDivElement>) {
    const rect = buttonRef.current?.getBoundingClientRect()
    if (event.newState !== 'open' || !rect) return
    setPosition({ top: rect.bottom + 6, left: rect.right })
    // Баланс меняется после покупок и выдачи заказов — перезапрашиваем при каждом открытии
    walletApi.balance().then(setBalance, () => setBalance(null))
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
        <BalanceBlock balance={balance} />
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

/** Баланс для покупок: всего (деньги + бонусы) и бонусы отдельно. Заморожено — выручка продавца. */
function BalanceBlock({ balance }: { balance: Balance | null | undefined }) {
  if (balance === null) return <p className="user-menu__balance-error">Не удалось загрузить баланс</p>
  return (
    <div className="user-menu__balance" aria-busy={balance === undefined}>
      <div>
        <span className="user-menu__balance-label">Всего</span>
        <span className="user-menu__balance-value">{balance ? formatPrice(balance.spendable) : '…'}</span>
      </div>
      <div>
        <span className="user-menu__balance-label">Бонусы</span>
        <span className="user-menu__balance-value">{balance ? formatPrice(balance.bonus) : '…'}</span>
      </div>
      {balance && Number(balance.frozen) > 0 && (
        <span className="user-menu__balance-note" title="Выручка за заказы, которые ещё не выданы">
          Заморожено {formatPrice(balance.frozen)}
        </span>
      )}
    </div>
  )
}
