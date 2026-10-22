import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { getErrorMessage } from '@/shared/api'
import { useCart } from './useCart'
import './CartControl.css'

interface CartControlProps {
  productId: number
  /** full — большая кнопка на странице товара, compact — круглая в углу плитки, row — счётчик в строке корзины */
  variant?: 'full' | 'compact' | 'row'
  /** Можно ли сейчас купить (в наличии и на продаже) */
  canBuy?: boolean
  /** Сколько есть в наличии — «+» блокируется на этом числе. Не знаем — проверит сервер. */
  max?: number
}

// Ошибку у плитки показываем коротко и убираем — места под неё там нет
const COMPACT_ERROR_MS = 4000

/**
 * «В корзину» и количество этого товара в корзине. Пока товара в корзине нет — кнопка,
 * потом — счётчик «− N +». Гостя отправляет на вход и возвращает обратно.
 */
export function CartControl({ productId, variant = 'full', canBuy = true, max }: CartControlProps) {
  const cart = useCart()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState<string | null>(null)

  const compact = variant === 'compact'
  const quantity = cart.quantityOf(productId)
  const busy = cart.isPending(productId) || cart.status === 'loading'
  const canAddMore = canBuy && (max === undefined || quantity < max)

  useEffect(() => {
    if (!compact || !error) return
    const timer = setTimeout(() => setError(null), COMPACT_ERROR_MS)
    return () => clearTimeout(timer)
  }, [compact, error])

  async function change(action: () => Promise<void>) {
    setError(null)
    try {
      await action()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  function handleAdd() {
    if (cart.status === 'anonymous') {
      navigate('/login', { state: { from: location.pathname + location.search } })
      return
    }
    void change(() => cart.add(productId))
  }

  const errorNode = error && (
    <span className="cart-control__error" role="alert">
      {error}
    </span>
  )

  // Товара нет в корзине
  if (quantity === 0) {
    if (!canBuy) {
      return compact ? null : (
        <div className="cart-control cart-control--full">
          <button type="button" className="cart-control__add cart-control__add--unavailable" disabled>
            Нет в наличии
          </button>
        </div>
      )
    }
    return (
      <div className={`cart-control cart-control--${variant}`}>
        <button
          type="button"
          className="cart-control__add"
          onClick={handleAdd}
          disabled={busy}
          aria-label={compact ? 'Добавить в корзину' : undefined}
          title={compact ? 'Добавить в корзину' : undefined}
        >
          {compact ? <CartPlusIcon /> : 'Добавить в корзину'}
        </button>
        {errorNode}
      </div>
    )
  }

  // Уже в корзине: «− N +»
  return (
    <div className={`cart-control cart-control--${variant}`}>
      {variant === 'full' && <span className="cart-control__label">В корзине</span>}
      <div className="cart-control__stepper" role="group" aria-label="Количество в корзине">
        <button
          type="button"
          className="cart-control__step"
          onClick={() => change(() => cart.setQuantity(productId, quantity - 1))}
          disabled={busy}
          aria-label={quantity === 1 ? 'Убрать из корзины' : 'Меньше'}
        >
          −
        </button>
        <span className="cart-control__count" aria-live="polite">
          {quantity}
          {!compact && ' шт.'}
        </span>
        <button
          type="button"
          className="cart-control__step"
          onClick={() => change(() => cart.add(productId))}
          disabled={busy || !canAddMore}
          aria-label="Больше"
          title={canAddMore ? undefined : 'Больше нет в наличии'}
        >
          +
        </button>
      </div>
      {variant === 'full' && !canAddMore && canBuy && <span className="cart-control__hint">Больше нет в наличии</span>}
      {errorNode}
    </div>
  )
}

function CartPlusIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="cart-control__icon">
      <path d="M2 3h3.2l.8 3H13v2H6.5l2.1 7h9.8l1.4-5h2.1l-2 7H7.6L4.6 5H2V3zm6.5 14a2 2 0 110 4 2 2 0 010-4zm9 0a2 2 0 110 4 2 2 0 010-4zM18 2h2v3h3v2h-3v3h-2V7h-3V5h3V2z" />
    </svg>
  )
}
