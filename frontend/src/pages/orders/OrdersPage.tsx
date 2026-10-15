import { EmptyState, LinkButton } from '@/shared/ui'

/** Заказы покупателя. API покупательских заказов ещё нет — пока заглушка. */
export function OrdersPage() {
  return (
    <EmptyState
      title="Заказы скоро появятся"
      text="Здесь будет история ваших покупок."
      action={<LinkButton to="/">На главную</LinkButton>}
    />
  )
}
