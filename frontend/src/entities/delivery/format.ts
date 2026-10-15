import type { DeliveryMethod } from '@/shared/api'
import { formatPrice, pluralize } from '@/shared/lib'

const DAY_WORDS: [string, string, string] = ['день', 'дня', 'дней']

/** Условия способа одной строкой: «бесплатно · 1–3 дня» */
export function formatDeliveryTerms(method: DeliveryMethod): string {
  const parts = [Number(method.price) === 0 ? 'бесплатно' : formatPrice(method.price)]
  if (method.eta) {
    const { min_days: min, max_days: max } = method.eta
    parts.push(min === max ? pluralize(min, DAY_WORDS) : `${min}–${pluralize(max, DAY_WORDS)}`)
  }
  return parts.join(' · ')
}
