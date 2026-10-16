import type { DeliveryMethod } from '@/shared/api'
import { formatPrice, pluralize } from '@/shared/lib'

const DAY_WORDS: [string, string, string] = ['день', 'дня', 'дней']

/** Условия способа одной строкой: «бесплатно · 1–3 дня» */
export function formatDeliveryTerms(method: DeliveryMethod): string {
  const parts = [formatDeliveryPrice(method.price)]
  if (method.eta) {
    const { min_days: min, max_days: max } = method.eta
    parts.push(min === max ? pluralize(min, DAY_WORDS) : `${min}–${pluralize(max, DAY_WORDS)}`)
  }
  return parts.join(' · ')
}

const dayFormatter = new Intl.DateTimeFormat('ru-RU', { weekday: 'short', day: 'numeric', month: 'short' })

/** «Сегодня», «Завтра» или «пт, 17 окт.» для даты YYYY-MM-DD */
export function formatSlotDay(date: string): string {
  const [year, month, day] = date.split('-').map(Number)
  // Дата без времени — разбираем как местную, иначе UTC сдвинет её на день
  const value = new Date(year, month - 1, day)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = Math.round((value.getTime() - today.getTime()) / 86_400_000)
  if (diff === 0) return 'Сегодня'
  if (diff === 1) return 'Завтра'
  return dayFormatter.format(value)
}

/** «Завтра, 10:00–14:00» */
export function formatSlot(slot: { date: string; start: string; end: string }): string {
  return `${formatSlotDay(slot.date)}, ${slot.start}–${slot.end}`
}

/** Цена доставки: 0 — «бесплатно» */
export function formatDeliveryPrice(price: string): string {
  return Number(price) === 0 ? 'бесплатно' : formatPrice(price)
}
