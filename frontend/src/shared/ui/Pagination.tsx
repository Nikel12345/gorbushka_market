import { Button } from './Button'

interface PaginationProps {
  page: number
  total: number
  hasPrevious: boolean
  hasNext: boolean
  disabled?: boolean
  onChange: (page: number) => void
}

/** Пагинация по next/previous из DRF: размер страницы задаёт бэкенд. */
export function Pagination({ page, total, hasPrevious, hasNext, disabled, onChange }: PaginationProps) {
  if (!hasPrevious && !hasNext) {
    return <div className="ui-pagination">Всего: {total}</div>
  }

  return (
    <nav className="ui-pagination" aria-label="Страницы">
      <span className="ui-pagination__total">Всего: {total}</span>
      <Button disabled={disabled || !hasPrevious} onClick={() => onChange(page - 1)}>
        ‹ Назад
      </Button>
      <span>Страница {page}</span>
      <Button disabled={disabled || !hasNext} onClick={() => onChange(page + 1)}>
        Вперёд ›
      </Button>
    </nav>
  )
}
