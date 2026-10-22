import { currencyApi, type UsdRate } from '@/shared/api'
import { formatDate, formatPrice, useRequest } from '@/shared/lib'
import { Field } from '@/shared/ui'

const loadRate = (signal: AbortSignal) => currencyApi.usd({ signal })

const rateFormatter = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 4 })

interface UsdPriceFieldProps {
  value: string
  onChange: (value: string) => void
  errors?: string[]
}

/** Цена товара в долларах — так она хранится; под полем — сколько это в рублях для покупателя */
export function UsdPriceField({ value, onChange, errors }: UsdPriceFieldProps) {
  const rate = useRequest(loadRate)

  return (
    <Field label="Цена, $" errors={errors} hint={rubHint(value, rate.data)}>
      <input
        className="ui-input"
        inputMode="decimal"
        placeholder="0,00"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={Boolean(errors)}
      />
    </Field>
  )
}

/** «≈ 79 990 ₽ для покупателя, курс ЦБ на 21 окт. 2026 г.: 82,8879 ₽ за $». Сервер ещё округляет по своему шагу */
function rubHint(value: string, rate: UsdRate | undefined): string | undefined {
  if (!rate) return undefined
  const source = rate.date ? `курс ЦБ на ${formatDate(rate.date)}` : 'курс магазина'
  const course = `${source}: ${rateFormatter.format(Number(rate.rate))} ₽ за $`
  const usd = Number(value.replace(/\s/g, '').replace(',', '.'))
  if (!value.trim() || !Number.isFinite(usd) || usd <= 0) return `Покупатель видит цену в рублях, ${course}`
  return `≈ ${formatPrice(Math.round(usd * Number(rate.rate)))} для покупателя, ${course}`
}
