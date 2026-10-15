import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  actions?: ReactNode
  /** Без внутренних отступов — для таблиц и списков во всю ширину */
  flush?: boolean
  children: ReactNode
}

export function Card({ title, actions, flush = false, children }: CardProps) {
  return (
    <section className={flush ? 'ui-card ui-card--flush' : 'ui-card'}>
      {(title || actions) && (
        <header className="ui-card__header">
          {title && <h2 className="ui-card__title">{title}</h2>}
          {actions && <div className="ui-card__actions">{actions}</div>}
        </header>
      )}
      <div className="ui-card__body">{children}</div>
    </section>
  )
}
