import { useEffect, useState } from 'react'
import { Link } from 'react-router'
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
 * потом — счётчик «− N +», а на странице товара под ним — «Перейти в корзину».
 * Работает и у гостя: входить не нужно до оформления заказа.
 */
export function CartControl({ productId, variant = 'full', canBuy = true, max }: CartControlProps) {
  const cart = useCart()
  const [error, setError] = useState<string | null>(null)
  // Смену «кнопка ↔ счётчик» анимируем только после нажатия, а не при первой отрисовке и догрузке корзины
  const [animated, setAnimated] = useState(false)

  const compact = variant === 'compact'
  const quantity = cart.quantityOf(productId)
  const inCart = quantity > 0
  const busy = cart.isPending(productId) || cart.status === 'loading'
  const canAddMore = canBuy && (max === undefined || quantity < max)

  useEffect(() => {
    if (!compact || !error) return
    const timer = setTimeout(() => setError(null), COMPACT_ERROR_MS)
    return () => clearTimeout(timer)
  }, [compact, error])

  async function change(action: () => Promise<void>) {
    setError(null)
    setAnimated(true)
    try {
      await action()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const className = `cart-control cart-control--${variant}${animated ? ' cart-control--animated' : ''}`

  const errorNode = error && (
    <span className="cart-control__error" role="alert">
      {error}
    </span>
  )

  // Страница товара: «Перейти в корзину» под счётчиком. Есть всегда, чтобы плавно раскрываться и сворачиваться
  const goToCart = variant === 'full' && (
    <div className={inCart ? 'cart-control__go cart-control__go--open' : 'cart-control__go'} inert={!inCart}>
      <div className="cart-control__go-inner">
        <Link to="/cart" className="cart-control__go-link">
          Перейти в корзину
        </Link>
      </div>
    </div>
  )

  // Товара нет в корзине
  if (!inCart) {
    if (!canBuy) {
      return compact ? null : (
        <div className={className}>
          <button type="button" className="cart-control__add cart-control__add--unavailable" disabled>
            Нет в наличии
          </button>
          {goToCart}
        </div>
      )
    }
    return (
      <div className={className}>
        <button
          type="button"
          className="cart-control__add"
          onClick={() => change(() => cart.add(productId))}
          disabled={busy}
          aria-label={compact ? 'Добавить в корзину' : undefined}
          title={compact ? 'Добавить в корзину' : undefined}
        >
          {compact ? <CartPlusIcon /> : 'Добавить в корзину'}
        </button>
        {goToCart}
        {errorNode}
      </div>
    )
  }

  // Уже в корзине: «− N +»
  return (
    <div className={className}>
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
      {goToCart}
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
