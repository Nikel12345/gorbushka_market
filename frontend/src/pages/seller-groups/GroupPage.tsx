import { useCallback, useState } from 'react'
import { useParams } from 'react-router'
import { BackButton, GroupFormDialog, GroupProducts } from '@/features/seller'
import { adminApi, ApiError, getErrorMessage } from '@/shared/api'
import { useRequest } from '@/shared/lib'
import { Button, Card, EmptyState, ErrorState, LinkButton, Loader, PageHeader } from '@/shared/ui'
import './SellerGroupsPage.css'

const LIST_PATH = '/seller/groups'

/** Группа вариантов: оси, товары таблицей, добавление товара в группу. */
export function GroupPage() {
  const groupId = Number(useParams().groupId)
  const load = useCallback((signal: AbortSignal) => adminApi.getGroup(groupId, { signal }), [groupId])
  const group = useRequest(load)
  const [editing, setEditing] = useState(false)

  if (group.status === 'error' || !group.data || group.data.id !== groupId) {
    const notFound = group.error instanceof ApiError && group.error.status === 404
    return (
      <>
        <BackButton fallback={LIST_PATH} />
        <Card>
          {group.status !== 'error' ? (
            <Loader />
          ) : notFound ? (
            <EmptyState title="Группа не найдена" action={<LinkButton to={LIST_PATH}>К группам</LinkButton>} />
          ) : (
            <ErrorState message={getErrorMessage(group.error)} onRetry={group.reload} />
          )}
        </Card>
      </>
    )
  }

  const g = group.data
  const axes = `различаются по: ${g.axes.map((axis) => axis.name).join(', ')}`

  return (
    <>
      <BackButton fallback={LIST_PATH} />
      <PageHeader
        title={g.name}
        subtitle={g.category ? `${g.category.name} · ${axes}` : `Без категории · ${axes}`}
        actions={
          <>
            <Button onClick={() => setEditing(true)}>Изменить</Button>
            <LinkButton variant="primary" to={`/seller/products/new?group=${g.id}`}>
              + Товар в группу
            </LinkButton>
          </>
        }
      />

      <Card title="Товары группы" flush>
        <GroupProducts group={g} withCopy />
      </Card>
      <p className="groups-hint">
        Быстрее всего завести новый вариант через «+ Вариант» у похожего товара: поля скопируются, останется
        поменять характеристики и фото.
      </p>

      {editing && (
        <GroupFormDialog
          group={g}
          onClose={() => setEditing(false)}
          onSaved={(updated) => {
            group.mutate(() => updated)
            setEditing(false)
          }}
        />
      )}
    </>
  )
}
