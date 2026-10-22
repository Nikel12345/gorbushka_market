import { getErrorMessage } from '@/shared/api'
import { Button } from '@/shared/ui'
import type { CategoriesRequest } from './categories'
import './catalogAdmin.css'

interface CategorySelectProps {
  categories: CategoriesRequest
  value: number | null
  onChange: (categoryId: number | null) => void
  /** Пункт «без категории»: «Без категории», «Во всех категориях», «Верхний уровень» */
  emptyLabel: string
  /** Эти выбрать нельзя — например, при переносе саму категорию и её подкатегории */
  disabledIds?: Set<number>
  invalid?: boolean
  disabled?: boolean
}

/** Выбор категории из дерева: подкатегории с отступом под родителем. */
export function CategorySelect({
  categories,
  value,
  onChange,
  emptyLabel,
  disabledIds,
  invalid,
  disabled,
}: CategorySelectProps) {
  if (!categories.data) {
    const failed = categories.status === 'error'
    return (
      <span className="category-select">
        <select className="ui-input" disabled>
          <option>{failed ? 'Категории не загрузились' : 'Загружаем категории…'}</option>
        </select>
        {failed && (
          <Button onClick={categories.reload} title={getErrorMessage(categories.error)}>
            Повторить
          </Button>
        )}
      </span>
    )
  }

  return (
    <select
      className="ui-input"
      value={value ?? ''}
      onChange={(event) => onChange(event.target.value ? Number(event.target.value) : null)}
      aria-invalid={invalid}
      disabled={disabled}
    >
      <option value="">{emptyLabel}</option>
      {categories.data.map((category) => (
        <option key={category.id} value={category.id} disabled={disabledIds?.has(category.id)}>
          {`${' '.repeat(4 * category.depth)}${category.name}`}
        </option>
      ))}
    </select>
  )
}
