import type { ReactNode } from 'react'

export interface OrderSummaryRow {
  label: ReactNode
  value: ReactNode
}

interface OrderSummaryProps {
  title: string
  rows: OrderSummaryRow[]
  /** Итог, уже отформатированный */
  total: ReactNode
  /** Примечания и кнопка под итогом */
  children?: ReactNode
}

/** Блок «Ваш заказ»: строки сумм, итог, действие. Прилипает под шапкой. Корзина и оформление. */
export function OrderSummary({ title, rows, total, children }: OrderSummaryProps) {
  return (
    <aside className="ui-summary" aria-label="Итого">
      <h2 className="ui-summary__title">{title}</h2>
      <dl className="ui-summary__rows">
        {rows.map((row, index) => (
          <SummaryRow key={index} {...row} />
        ))}
      </dl>
      <div className="ui-summary__total">
        <span>Итого</span>
        <span>{total}</span>
      </div>
      {children}
    </aside>
  )
}

function SummaryRow({ label, value }: OrderSummaryRow) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  )
}
