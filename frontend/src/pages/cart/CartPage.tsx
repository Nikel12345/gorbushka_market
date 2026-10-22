import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { ProductImage } from '@/entities/product'
import { CartControl, useCart } from '@/features/cart'
import { getErrorMessage, type CartLine } from '@/shared/api'
import { formatPrice, pluralize } from '@/shared/lib'
import { Button, EmptyState, ErrorState, FieldError, LinkButton, Loader, OrderSummary } from '@/shared/ui'
import './CartPage.css'

const ITEM_WORDS: [string, string, string] = ['товар', 'товара', 'товаров']

/** Корзина: позиции слева, итог и переход к оформлению справа. */
export function CartPage() {
  const { status, cart, refresh, clear } = useCart()
  const [confirmClear, setConfirmClear] = useState(false)
  const [clearError, setClearError] = useState<string>()

  // Наличие и цены могли измениться, пока корзина лежала в памяти — перезапрашиваем при входе
  useEffect(() => {
    refresh()
  }, [refresh])

  async function handleClear() {
    setClearError(undefined)
    try {
      await clear()
      setConfirmClear(false)
    } catch (error) {
      setClearError(getErrorMessage(error))
    }
  }

  if (!cart) {
    return status === 'error' ? (
      <ErrorState message="Не удалось загрузить корзину." onRetry={refresh} />
    ) : (
      <Loader />
    )
  }

  if (cart.items.length === 0) {
    return (
      <EmptyState
        title="В корзине пока пусто"
        text="Загляните в каталог на главной."
        action={
          <LinkButton variant="primary" to="/">
            Перейти к покупкам
          </LinkButton>
        }
      />
    )
  }

  const availableLines = cart.items.filter((line) => line.is_available)
  const availableCount = availableLines.reduce((sum, line) => sum + line.quantity, 0)

  return (
    <>
      <div className="cart-page__header">
        <h1 className="cart-page__title">
          Корзина <span className="cart-page__count">{pluralize(cart.items_count, ITEM_WORDS)}</span>
        </h1>
        {confirmClear ? (
          <span className="cart-page__confirm">
            Убрать все товары?
            <Button variant="text" onClick={() => setConfirmClear(false)}>
              Нет
            </Button>
            <Button variant="danger" onClick={handleClear}>
              Очистить
            </Button>
          </span>
        ) : (
          <Button variant="text" onClick={() => setConfirmClear(true)}>
            Очистить корзину
          </Button>
        )}
      </div>
      <FieldError messages={clearError ? [clearError] : undefined} />

      <div className="cart-page">
        <ul className="cart-page__lines">
          {cart.items.map((line) => (
            <CartLineRow key={line.product.id} line={line} />
          ))}
        </ul>

        <OrderSummary
          title="Ваш заказ"
          rows={[{ label: `Товары, ${pluralize(availableCount, ITEM_WORDS)}`, value: formatPrice(cart.total_amount) }]}
          total={formatPrice(cart.total_amount)}
        >
          {cart.has_unavailable && (
            <p className="ui-summary__note">
              Часть товаров сейчас недоступна — они не войдут в заказ и не учтены в сумме.
            </p>
          )}
          {availableLines.length > 0 ? (
            <LinkButton variant="primary" to="/checkout" className="ui-summary__action">
              Перейти к оформлению
            </LinkButton>
          ) : (
            <Button variant="primary" className="ui-summary__action" disabled>
              Перейти к оформлению
            </Button>
          )}
        </OrderSummary>
      </div>
    </>
  )
}

function CartLineRow({ line }: { line: CartLine }) {
  const { remove, isPending } = useCart()
  const [error, setError] = useState<string>()
  const { product } = line
  const productUrl = `/products/${product.id}`

  async function handleRemove() {
    setError(undefined)
    try {
      await remove(product.id)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  let availability = null
  if (!line.is_available) {
    availability =
      line.available_quantity === 0
        ? 'Нет в наличии'
        : `Доступно только ${line.available_quantity} шт. — уменьшите количество`
  }

  return (
    <li className={line.is_available ? 'cart-line' : 'cart-line cart-line--unavailable'}>
      <Link to={productUrl} className="cart-line__image" tabIndex={-1} aria-hidden="true">
        <ProductImage src={product.image} alt="" />
      </Link>

      <div className="cart-line__info">
        <Link to={productUrl} className="cart-line__title">
          {product.title}
        </Link>
        <span className="cart-line__unit">{formatPrice(product.price)} / шт.</span>
        {availability && <span className="cart-line__warning">{availability}</span>}
      </div>

      <div className="cart-line__quantity">
        <CartControl
          productId={product.id}
          variant="row"
          canBuy={line.available_quantity > 0}
          max={line.available_quantity}
        />
      </div>

      <div className="cart-line__side">
        <span className="cart-line__total">{formatPrice(line.total)}</span>
        <button type="button" className="cart-line__remove" onClick={handleRemove} disabled={isPending(product.id)}>
          Удалить
        </button>
        <FieldError messages={error ? [error] : undefined} />
      </div>
    </li>
  )
}
