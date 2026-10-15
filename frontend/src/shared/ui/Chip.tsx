import type { ReactNode } from 'react'

export type ChipTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'

/** Небольшая плашка статуса. */
export function Chip({ tone = 'neutral', children }: { tone?: ChipTone; children: ReactNode }) {
  return <span className={`ui-chip ui-chip--${tone}`}>{children}</span>
}
