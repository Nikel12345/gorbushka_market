import { EmptyState, LinkButton } from '@/shared/ui'

/** Оформление заказа. На бэкенде пока нет создания заказа из корзины — заглушка. */
export function CheckoutPage() {
  return (
    <EmptyState
      title="Оформление заказа скоро появится"
      text="Товары остаются в корзине — вернуться к ним можно в любой момент."
      action={<LinkButton to="/cart">Вернуться в корзину</LinkButton>}
    />
  )
}
