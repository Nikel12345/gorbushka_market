import type { OrderBase, OrderStatus, OrderStatusOption, PaymentStatus } from '@/shared/api'
import type { ChipTone } from '@/shared/ui'

/** Цвет плашки статуса заказа — одинаковый у продавца и покупателя */
export const ORDER_STATUS_TONE: Record<OrderStatus, ChipTone> = {
  new: 'info',
  confirmed: 'warning',
  ready: 'warning',
  completed: 'success',
  cancelled: 'neutral',
}

export const PAYMENT_STATUS_TONE: Record<PaymentStatus, ChipTone> = {
  unpaid: 'warning',
  paid: 'success',
  refunded: 'neutral',
}

/** Кто доставляет заказ. Заказы до появления доставки ведёт продавец (как самовывоз). */
export function orderProvider(order: OrderBase): 'shop' | 'market' {
  return order.shipment?.delivery_method.provider ?? 'shop'
}

// Этапы как в orders.statuses на бэкенде: названия «готов» и «выполнен» зависят от доставки
const STEP_LABELS: Record<'shop' | 'market', string[]> = {
  shop: ['Новый', 'Подтверждён', 'Готов к выдаче', 'Выдан'],
  market: ['Новый', 'Подтверждён', 'Передан курьеру', 'Доставлен'],
}
const STEP_STATUSES: OrderStatus[] = ['new', 'confirmed', 'ready', 'completed']

/** Путь заказа для полоски прогресса. У отменённого пути нет. */
export function orderSteps(order: OrderBase): { status: OrderStatus; label: string; done: boolean }[] {
  const current = STEP_STATUSES.indexOf(order.status)
  return STEP_LABELS[orderProvider(order)].map((label, index) => ({
    status: STEP_STATUSES[index],
    label,
    done: index <= current,
  }))
}

/** Текст кнопки перехода: глагол там, где он понятнее названия статуса */
export function statusActionLabel(option: OrderStatusOption): string {
  if (option.status === 'confirmed') return 'Подтвердить'
  if (option.status === 'cancelled') return 'Отменить'
  return option.name
}
