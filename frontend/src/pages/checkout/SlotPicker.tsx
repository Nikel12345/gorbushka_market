import { useCallback, useState } from 'react'
import { formatSlotDay } from '@/entities/delivery'
import { deliveryApi, getErrorMessage, type DeliveryMethod, type DeliverySlot } from '@/shared/api'
import { useRequest } from '@/shared/lib'
import { FieldError, Loader } from '@/shared/ui'

export interface SlotValue {
  date: string
  window_id: number
}

interface SlotPickerProps {
  method: DeliveryMethod
  value: SlotValue | undefined
  onChange: (value: SlotValue) => void
  errors?: string[]
}

/** Время доставки: день, затем интервал. Свободное время отдаёт сервер. */
export function SlotPicker({ method, value, onChange, errors }: SlotPickerProps) {
  const load = useCallback((signal: AbortSignal) => deliveryApi.slots(method.id, { signal }), [method.id])
  const slots = useRequest(load)
  const [openedDay, setOpenedDay] = useState<string | null>(null)

  if (!slots.data) {
    return slots.status === 'error' ? (
      <FieldError messages={[getErrorMessage(slots.error)]} />
    ) : (
      <Loader label="Загружаем время доставки…" />
    )
  }

  const byDay = new Map<string, DeliverySlot[]>()
  for (const slot of slots.data) byDay.set(slot.date, [...(byDay.get(slot.date) ?? []), slot])
  const days = [...byDay.keys()]
  if (days.length === 0) {
    return <FieldError messages={['Свободного времени нет — выберите другой способ получения.']} />
  }

  const day = openedDay ?? value?.date ?? days[0]

  return (
    <div className="checkout-slots">
      <span className="ui-field__label">Время доставки</span>
      <div className="checkout-slots__row" role="group" aria-label="День">
        {days.map((date) => (
          <button
            key={date}
            type="button"
            className="checkout-slots__chip"
            aria-pressed={date === day}
            onClick={() => setOpenedDay(date)}
          >
            {formatSlotDay(date)}
          </button>
        ))}
      </div>
      <div className="checkout-slots__row" role="group" aria-label="Интервал">
        {(byDay.get(day) ?? []).map((slot) => (
          <button
            key={slot.window_id}
            type="button"
            className="checkout-slots__chip"
            aria-pressed={value?.date === slot.date && value.window_id === slot.window_id}
            onClick={() => onChange({ date: slot.date, window_id: slot.window_id })}
          >
            {slot.start}–{slot.end}
          </button>
        ))}
      </div>
      <FieldError messages={errors} />
    </div>
  )
}
