import { useCallback, useState } from 'react'
import { GroupFormDialog } from '@/features/seller'
import { adminApi, getErrorMessage, type ProductGroup } from '@/shared/api'
import { useDebouncedValue, useRequest } from '@/shared/lib'
import { Button } from '@/shared/ui'

interface GroupPickerProps {
  /** Выбранная группа; null — без группы, undefined — загружается */
  group: ProductGroup | null | undefined
  /** Выбранную группу не удалось загрузить */
  error?: unknown
  /** Категория товара: в поиске — только подходящие ей группы */
  categoryId: number | null
  /** Группа не подходит категории товара */
  mismatch?: boolean
  onRetry: () => void
  onChange: (group: ProductGroup | null) => void
}

/** Группа вариантов товара: показать, сменить (поиск или новая группа), убрать. */
export function GroupPicker({ group, error, categoryId, mismatch, onRetry, onChange }: GroupPickerProps) {
  const [picking, setPicking] = useState(false)

  if (picking) {
    return (
      <GroupSearch
        categoryId={categoryId}
        onPick={(picked) => {
          onChange(picked)
          setPicking(false)
        }}
        onCancel={() => setPicking(false)}
      />
    )
  }

  if (error) {
    return (
      <div className="group-picker group-picker--error">
        <span className="group-picker__info">Не удалось загрузить группу: {getErrorMessage(error)}</span>
        <Button onClick={onRetry}>Повторить</Button>
        <Button variant="text" onClick={() => onChange(null)}>
          Убрать из группы
        </Button>
      </div>
    )
  }

  if (group === undefined) return <span className="ui-field__hint">Загружаем группу…</span>

  let hint = 'Кнопок вариантов на витрине не будет. Выберите группу, если это другой цвет или объём уже заведённой модели.'
  if (group) {
    const axes = `различаются по: ${group.axes.map((axis) => axis.name).join(', ')}`
    hint = group.category ? `${group.category.name} · ${axes}` : `Без категории · ${axes}`
  }

  return (
    <div className="group-picker">
      <div className="group-picker__info">
        <span className="group-picker__name">
          {group ? group.name : 'Без группы'}
          {mismatch && <span className="category-note">не подходит категории товара</span>}
        </span>
        <span className="ui-field__hint">{hint}</span>
      </div>
      <Button onClick={() => setPicking(true)}>{group ? 'Сменить' : 'Выбрать группу'}</Button>
      {group && (
        <Button variant="text" onClick={() => onChange(null)}>
          Убрать из группы
        </Button>
      )}
    </div>
  )
}

/**
 * Поиск группы по названию по мере ввода; не нашлась — создать новую с этим названием.
 * У товара с категорией — только подходящие ей группы (без категории, её и категорий выше).
 */
function GroupSearch({
  categoryId,
  onPick,
  onCancel,
}: {
  categoryId: number | null
  onPick: (group: ProductGroup) => void
  onCancel: () => void
}) {
  const [query, setQuery] = useState('')
  const [creating, setCreating] = useState(false)
  const q = useDebouncedValue(query.trim())

  const load = useCallback(
    (signal: AbortSignal) => adminApi.listGroups({ q, category: categoryId ?? undefined }, { signal }),
    [q, categoryId],
  )
  const groups = useRequest(load)

  let results
  if (groups.status === 'error') {
    results = (
      <div className="group-picker group-picker--error">
        <span className="group-picker__info">Не удалось загрузить группы: {getErrorMessage(groups.error)}</span>
        <Button onClick={groups.reload}>Повторить</Button>
      </div>
    )
  } else if (!groups.data) {
    results = <span className="ui-field__hint">Ищем…</span>
  } else if (groups.data.results.length === 0) {
    let empty = 'Групп пока нет.'
    if (q) empty = 'Ничего не нашлось.'
    else if (categoryId !== null) empty = 'Для этой категории групп пока нет.'
    results = <span className="ui-field__hint">{empty}</span>
  } else {
    const shown = groups.data.results.length
    results = (
      <>
        <ul className={groups.status === 'loading' ? 'group-search__results group-search__results--dimmed' : 'group-search__results'}>
          {groups.data.results.map((item) => (
            <li key={item.id}>
              <button type="button" className="group-search__result" onClick={() => onPick(item)}>
                <span className="group-search__name">{item.name}</span>
                <span className="group-search__axes">
                  {[item.category?.name, item.axes.map((axis) => axis.name).join(', ')].filter(Boolean).join(' · ')}
                </span>
              </button>
            </li>
          ))}
        </ul>
        {groups.data.count > shown && (
          <span className="ui-field__hint">
            Показаны первые {shown} из {groups.data.count} — уточните поиск.
          </span>
        )}
      </>
    )
  }

  return (
    <div className="group-search">
      <div className="group-search__bar">
        <input
          className="ui-input"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.preventDefault()
              onCancel()
            }
          }}
          placeholder="Найти группу по названию"
          aria-label="Поиск группы вариантов"
          autoFocus
        />
        <Button variant="text" onClick={onCancel}>
          Отмена
        </Button>
      </div>
      {results}
      <Button className="group-search__create" onClick={() => setCreating(true)}>
        + Новая группа{query.trim() && ` «${query.trim()}»`}
      </Button>
      {creating && (
        <GroupFormDialog
          initialName={query.trim()}
          initialCategoryId={categoryId}
          onClose={() => setCreating(false)}
          onSaved={onPick}
        />
      )}
    </div>
  )
}
