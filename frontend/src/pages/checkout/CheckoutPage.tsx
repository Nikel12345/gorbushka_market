import { useState } from 'react'
import { useCart } from '@/features/cart'
import { checkoutApi, getErrorMessage, type Purchase } from '@/shared/api'
import { useRequest } from '@/shared/lib'
import { EmptyState, ErrorState, LinkButton, Loader } from '@/shared/ui'
import { CheckoutForm } from './CheckoutForm'
import { CheckoutSuccess } from './CheckoutSuccess'
import './CheckoutPage.css'

const loadPreview = (signal: AbortSignal) => checkoutApi.get({ signal })

/** Оформление покупки из корзины: /checkout */
export function CheckoutPage() {
  const { refresh: refreshCart } = useCart()
  const preview = useRequest(loadPreview)
  const [purchase, setPurchase] = useState<Purchase | null>(null)

  if (purchase) return <CheckoutSuccess purchase={purchase} />

  if (!preview.data) {
    return preview.status === 'error' ? (
      <ErrorState message={getErrorMessage(preview.error)} onRetry={preview.reload} />
    ) : (
      <Loader />
    )
  }

  if (!preview.data.can_checkout) {
    const unavailable = preview.data.unavailable_items
    const hasItems = unavailable.length > 0
    // Причину показываем: корзина её не знает (например, свой товар или нет способа доставки)
    const reasons = unavailable.map((item) => `«${item.product.title}» — ${item.problem.detail}`).join(' ')
    return (
      <EmptyState
        title="Нечего оформлять"
        text={hasItems ? reasons : 'Корзина пуста.'}
        action={<LinkButton to={hasItems ? '/cart' : '/'}>{hasItems ? 'В корзину' : 'На главную'}</LinkButton>}
      />
    )
  }

  return (
    <CheckoutForm
      preview={preview.data}
      onStale={preview.reload}
      onPlaced={(placed) => {
        setPurchase(placed)
        refreshCart()
        window.scrollTo(0, 0)
      }}
    />
  )
}
