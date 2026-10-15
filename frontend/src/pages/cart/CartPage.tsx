import { EmptyState, LinkButton } from '@/shared/ui'

/** Корзина покупателя. API корзины ещё нет — пока заглушка. */
export function CartPage() {
  return (
    <EmptyState
      title="Корзина скоро появится"
      text="Раздел в разработке."
      action={<LinkButton to="/">На главную</LinkButton>}
    />
  )
}
