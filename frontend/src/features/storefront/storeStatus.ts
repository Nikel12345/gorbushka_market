import { store } from '@/shared/config'

const moscowTime = new Intl.DateTimeFormat('ru-RU', {
  timeZone: 'Europe/Moscow',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

function toMinutes(time: string): number {
  const [hours, minutes] = time.split(':').map(Number)
  return hours * 60 + (minutes || 0)
}

/** Открыт ли магазин сейчас (по Москве) — по часам из store.hours «10:00–21:00» */
export function getStoreStatus(now = new Date()): { open: boolean; text: string } {
  const [opens, closes] = store.hours.split(/[–-]/).map((part) => part.trim())
  const parts = moscowTime.formatToParts(now)
  const hour = Number(parts.find((part) => part.type === 'hour')?.value)
  const minute = Number(parts.find((part) => part.type === 'minute')?.value)
  const current = hour * 60 + minute
  const open = current >= toMinutes(opens) && current < toMinutes(closes)
  return { open, text: open ? `Открыто сегодня до ${closes}` : `Откроемся в ${opens}` }
}
