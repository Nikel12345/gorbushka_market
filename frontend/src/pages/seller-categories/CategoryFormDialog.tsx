import { useState, type FormEvent } from 'react'
import { CategorySelect, subtreeIds, type CategoriesRequest } from '@/features/seller'
import { adminApi, getFieldErrors, type Category, type CategoryPayload, type FieldErrors } from '@/shared/api'
import { Button, Dialog, Field, FieldError } from '@/shared/ui'

const FORM_ID = 'category-form'

interface CategoryFormDialogProps {
  /** Нет — новая категория */
  category?: Category
  /** Куда положить новую; null — на верхний уровень */
  parentId?: number | null
  categories: CategoriesRequest
  onClose: () => void
  onSaved: (category: Category) => void
}

/** Название категории, куда она вложена (перенос — тут же), адрес раздела и порядок среди соседей. */
export function CategoryFormDialog({ category, parentId = null, categories, onClose, onSaved }: CategoryFormDialogProps) {
  const [name, setName] = useState(category?.name ?? '')
  const [parent, setParent] = useState<number | null>(category ? category.parent_id : parentId)
  const [slug, setSlug] = useState(category?.slug ?? '')
  const [sortOrder, setSortOrder] = useState(category ? String(category.sort_order) : '')
  const [errors, setErrors] = useState<FieldErrors>({})
  const [saving, setSaving] = useState(false)

  // Внутрь себя не перенести
  const ownBranch = category && categories.data ? subtreeIds(categories.data, category.id) : undefined
  const moved = category !== undefined && parent !== category.parent_id

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const localErrors: FieldErrors = {}
    if (!name.trim()) localErrors.name = ['Введите название.']
    if (!/^[-a-zA-Z0-9_]*$/.test(slug.trim())) localErrors.slug = ['Только латиница, цифры, дефис и подчёркивание.']
    if (sortOrder.trim() && !/^\d{1,4}$/.test(sortOrder.trim())) localErrors.sort_order = ['Целое число от 0 до 9999.']
    setErrors(localErrors)
    if (Object.keys(localErrors).length > 0) return

    const payload: CategoryPayload = { name: name.trim(), parent_id: parent }
    // Пустой адрес сервер сделает из названия заново
    if (category) payload.slug = slug.trim()
    if (sortOrder.trim()) payload.sort_order = Number(sortOrder)

    setSaving(true)
    try {
      onSaved(category ? await adminApi.updateCategory(category.id, payload) : await adminApi.createCategory(payload))
    } catch (error) {
      const fieldErrors = getFieldErrors(error)
      // Перенос внутрь себя (category_cycle) приходит общей ошибкой — показываем у поля
      if (fieldErrors.code?.[0] === 'category_cycle') {
        setErrors({ parent_id: fieldErrors.non_field_errors })
      } else {
        setErrors(fieldErrors)
      }
      setSaving(false)
    }
  }

  return (
    <Dialog
      title={category ? 'Категория' : 'Новая категория'}
      onClose={onClose}
      actions={
        <>
          <Button variant="text" onClick={onClose}>
            Отмена
          </Button>
          <Button type="submit" form={FORM_ID} variant="primary" disabled={saving}>
            {saving ? 'Сохраняем…' : category ? 'Сохранить' : 'Создать'}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} className="ui-form" onSubmit={handleSubmit} noValidate>
        <FieldError messages={errors.non_field_errors} />
        <Field label="Название" errors={errors.name}>
          <input
            className="ui-input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            aria-invalid={Boolean(errors.name)}
            maxLength={100}
            data-autofocus
          />
        </Field>
        <Field
          label="Внутри категории"
          errors={errors.parent_id}
          hint={
            moved
              ? 'Переедет вместе с подкатегориями и товарами. Что станет товарам недоступно, скроется с витрины — карточки товаров это отметят.'
              : undefined
          }
        >
          <CategorySelect
            categories={categories}
            value={parent}
            onChange={setParent}
            emptyLabel="Верхний уровень"
            disabledIds={ownBranch}
            invalid={Boolean(errors.parent_id)}
          />
        </Field>
        {category && (
          <Field
            label="Адрес раздела"
            errors={errors.slug}
            hint="Латиницей. Если сменить, старые ссылки на раздел перестанут работать. Пусто — сделаем из названия."
          >
            <input
              className="ui-input"
              value={slug}
              onChange={(event) => setSlug(event.target.value)}
              aria-invalid={Boolean(errors.slug)}
              maxLength={120}
              spellCheck={false}
            />
          </Field>
        )}
        <Field label="Порядок" errors={errors.sort_order} hint="Среди соседних категорий: чем меньше, тем выше.">
          <input
            className="ui-input"
            inputMode="numeric"
            placeholder="0"
            value={sortOrder}
            onChange={(event) => setSortOrder(event.target.value)}
            aria-invalid={Boolean(errors.sort_order)}
          />
        </Field>
      </form>
    </Dialog>
  )
}
