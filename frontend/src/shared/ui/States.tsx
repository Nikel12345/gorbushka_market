import type { ReactNode } from 'react'
import { Button } from './Button'

interface EmptyStateProps {
  title: string
  text?: string
  action?: ReactNode
}

export function EmptyState({ title, text, action }: EmptyStateProps) {
  return (
    <div className="ui-state">
      <p className="ui-state__title">{title}</p>
      {text && <p className="ui-state__text">{text}</p>}
      {action && <div className="ui-state__actions">{action}</div>}
    </div>
  )
}

interface ErrorStateProps {
  message: string
  onRetry?: () => void
  action?: ReactNode
}

export function ErrorState({ message, onRetry, action }: ErrorStateProps) {
  return (
    <div className="ui-state ui-state--error" role="alert">
      <p className="ui-state__title">Не удалось загрузить данные</p>
      <p className="ui-state__text">{message}</p>
      {(onRetry || action) && (
        <div className="ui-state__actions">
          {onRetry && (
            <Button variant="primary" onClick={onRetry}>
              Повторить
            </Button>
          )}
          {action}
        </div>
      )}
    </div>
  )
}
