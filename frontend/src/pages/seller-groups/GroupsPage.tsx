import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { GroupFormDialog } from '@/features/seller'
import { adminApi, ApiError, getErrorMessage } from '@/shared/api'
import { parsePage, pluralize, updateSearchParams, useRequest } from '@/shared/lib'
import { Button, Card, EmptyState, ErrorState, LinearProgress, Loader, PageHeader, Pagination } from '@/shared/ui'
import './SellerGroupsPage.css'

const GROUP_WORDS: [string, string, string] = ['группа', 'группы', 'групп']

/** Группы вариантов: поиск по названию, список, новая группа. Страница группы — /seller/groups/:groupId */
export function GroupsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const page = parsePage(searchParams.get('page'))
  const q = searchParams.get('q') ?? ''
  const [creating, setCreating] = useState(false)

  const load = useCallback((signal: AbortSignal) => adminApi.listGroups({ page, q }, { signal }), [page, q])
  const groups = useRequest(load)

  function goToPage(next: number) {
    setSearchParams((prev) => updateSearchParams(prev, { page: next > 1 ? next : null }))
  }

  let content
  if (groups.status === 'error') {
    const pageMissing = groups.error instanceof ApiError && groups.error.status === 404 && page > 1
    content = pageMissing ? (
      <EmptyState title="Такой страницы нет" action={<Button onClick={() => goToPage(1)}>К первой странице</Button>} />
    ) : (
      <ErrorState message={getErrorMessage(groups.error)} onRetry={groups.reload} />
    )
  } else if (!groups.data) {
    content = <Loader />
  } else if (groups.data.results.length === 0) {
    content = q ? (
      <EmptyState title="Ничего не найдено" text="Попробуйте другое название." />
    ) : (
      <EmptyState
        title="Групп пока нет"
        text="Группа объединяет товары одной модели, которые различаются цветом, памятью и т. п."
        action={
          <Button variant="primary" onClick={() => setCreating(true)}>
            Создать группу
          </Button>
        }
      />
    )
  } else {
    content = (
      <div className="ui-table-wrap">
        <table className="ui-table">
          <thead>
            <tr>
              <th>Название</th>
              <th>Категория</th>
              <th>Различаются по</th>
            </tr>
          </thead>
          <tbody>
            {groups.data.results.map((group) => (
              <tr
                key={group.id}
                className="ui-table__row--clickable"
                onClick={() => navigate(String(group.id))}
              >
                <td>
                  <Link to={String(group.id)} className="groups-table__name">
                    {group.name}
                  </Link>
                </td>
                <td>{group.category ? group.category.name : <span className="ui-muted">—</span>}</td>
                <td>{group.axes.map((axis) => axis.name).join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <>
      <PageHeader
        title="Группы вариантов"
        subtitle={
          groups.data
            ? pluralize(groups.data.count, GROUP_WORDS)
            : 'Товары одной модели, между которыми покупатель переключается кнопками'
        }
        actions={
          <Button variant="primary" onClick={() => setCreating(true)}>
            + Новая группа
          </Button>
        }
      />

      <GroupSearch
        value={q}
        onChange={(next) => setSearchParams((prev) => updateSearchParams(prev, { q: next, page: null }), { replace: true })}
      />

      <Card flush>
        <div className="groups-list">
          {groups.status === 'loading' && groups.data && <LinearProgress />}
          {content}
        </div>
      </Card>

      {groups.status !== 'error' && groups.data && groups.data.results.length > 0 && (
        <Pagination
          page={page}
          total={groups.data.count}
          hasPrevious={Boolean(groups.data.previous)}
          hasNext={Boolean(groups.data.next)}
          disabled={groups.status === 'loading'}
          onChange={goToPage}
        />
      )}

      {creating && (
        <GroupFormDialog onClose={() => setCreating(false)} onSaved={(group) => navigate(String(group.id))} />
      )}
    </>
  )
}

/** Поиск по мере ввода: в адрес уходит, когда пользователь перестал печатать */
function GroupSearch({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [text, setText] = useState(value)
  const timer = useRef<number>(undefined)
  useEffect(() => () => clearTimeout(timer.current), [])

  function handleChange(next: string) {
    setText(next)
    clearTimeout(timer.current)
    timer.current = window.setTimeout(() => onChange(next.trim()), 300)
  }

  return (
    <input
      className="ui-input groups-search"
      type="search"
      value={text}
      onChange={(event) => handleChange(event.target.value)}
      placeholder="Поиск по названию"
      aria-label="Поиск групп по названию"
    />
  )
}
