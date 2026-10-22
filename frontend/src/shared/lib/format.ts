const LOCALE = 'ru-RU'

const priceFormatter = new Intl.NumberFormat(LOCALE, {
  style: 'currency',
  currency: 'RUB',
  maximumFractionDigits: 0,
})
const priceWithKopecksFormatter = new Intl.NumberFormat(LOCALE, {
  style: 'currency',
  currency: 'RUB',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/** "79990.00" → "79 990 ₽", "99.50" → "99,50 ₽" */
export function formatPrice(value: string | number): string {
  const amount = typeof value === 'string' ? Number(value) : value
  if (!Number.isFinite(amount)) return String(value)
  return Number.isInteger(amount) ? priceFormatter.format(amount) : priceWithKopecksFormatter.format(amount)
}

const dateFormatter = new Intl.DateTimeFormat(LOCALE, { dateStyle: 'medium' })
const dateTimeFormatter = new Intl.DateTimeFormat(LOCALE, { dateStyle: 'medium', timeStyle: 'short' })

export function formatDate(iso: string): string {
  return dateFormatter.format(new Date(iso))
}

export function formatDateTime(iso: string): string {
  return dateTimeFormatter.format(new Date(iso))
}

interface PersonLike {
  email: string
  first_name: string
  last_name: string
}

/** Имя и фамилия, а если их нет — email. */
export function formatPersonName(person: PersonLike): string {
  return [person.first_name, person.last_name].filter(Boolean).join(' ') || person.email
}

const ratingFormatter = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** Средняя оценка: "4.75" → "4,8", 5 → "5,0" */
export function formatRating(value: string | number): string {
  return ratingFormatter.format(Number(value))
}

const pluralRules = new Intl.PluralRules(LOCALE)

/** pluralize(5, ['товар', 'товара', 'товаров']) → "5 товаров" */
export function pluralize(count: number, [one, few, many]: [string, string, string]): string {
  const rule = pluralRules.select(count)
  const word = rule === 'one' ? one : rule === 'few' ? few : many
  return `${count} ${word}`
}
