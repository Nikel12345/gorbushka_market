import { useState, type FormEvent } from 'react'
import {
  adminApi,
  getErrorMessage,
  getFieldErrors,
  type Characteristic,
  type FieldErrors,
  type ProductGroup,
} from '@/shared/api'
import { Button, Dialog, Field, FieldError } from '@/shared/ui'
import { isAvailableIn, useCategories } from './categories'
import { CategorySelect } from './CategorySelect'
import { useCharacteristics, withCharacteristic } from './characteristics'
import { InlineCreateField } from './InlineCreateField'
import './catalogAdmin.css'

const FORM_ID = 'group-form'

interface GroupFormDialogProps {
  /** Нет — новая группа */
  group?: ProductGroup
  /** Название новой группы — например, то, что искали */
  initialName?: string
  /** Категория новой группы — например, товара, из которого её создают */
  initialCategoryId?: number | null
  onClose: () => void
  onSaved: (group: ProductGroup) => void
}

/** Название группы вариантов, её категория и характеристики, по которым различаются её товары. */
export function GroupFormDialog({
  group,
  initialName = '',
  initialCategoryId = null,
  onClose,
  onSaved,
}: GroupFormDialogProps) {
  const characteristics = useCharacteristics()
  const categories = useCategories()
  const [name, setName] = useState(group?.name ?? initialName)
  const [categoryId, setCategoryId] = useState<number | null>(group ? (group.category?.id ?? null) : initialCategoryId)
  const [axisIds, setAxisIds] = useState<number[]>(() => group?.axes.map((axis) => axis.id) ?? [])
  const [addingAxis, setAddingAxis] = useState(false)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [saving, setSaving] = useState(false)

  function toggle(id: number, checked: boolean) {
    setAxisIds((ids) => (checked ? [...ids, id] : ids.filter((item) => item !== id)))
  }

  // Оси — из характеристик, доступных в категории группы. Отмеченные недоступные (сменили
  // категорию) остаются в списке с пометкой, чтобы их сняли сами, а не потеряли молча
  const available = (characteristic: Characteristic) =>
    !categories.data || isAvailableIn(categories.data, characteristic.category, categoryId)
  const shownAxes = characteristics.data?.filter((item) => available(item) || axisIds.includes(item.id)) ?? []
  const unavailableAxes = shownAxes.filter((item) => axisIds.includes(item.id) && !available(item))

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const localErrors: FieldErrors = {}
    if (!name.trim()) localErrors.name = ['Введите название.']
    if (axisIds.length === 0) {
      localErrors.axis_ids = ['Отметьте хотя бы одну характеристику.']
    } else if (unavailableAxes.length > 0) {
      const names = unavailableAxes.map((item) => `«${item.name}»`).join(', ')
      localErrors.axis_ids = [`Недоступны в выбранной категории: ${names}. Снимите отметку или выберите другую категорию.`]
    }
    setErrors(localErrors)
    if (Object.keys(localErrors).length > 0) return

    setSaving(true)
    try {
      const payload = { name: name.trim(), category_id: categoryId, axis_ids: axisIds }
      onSaved(group ? await adminApi.updateGroup(group.id, payload) : await adminApi.createGroup(payload))
    } catch (error) {
      setErrors(getFieldErrors(error))
      setSaving(false)
    }
  }

  let axesBody
  if (characteristics.status === 'error' || categories.status === 'error') {
    const failed = characteristics.status === 'error' ? characteristics : categories
    axesBody = (
      <div className="axes-field__error">
        <span>Не удалось загрузить характеристики: {getErrorMessage(failed.error)}</span>
        <Button onClick={failed.reload}>Повторить</Button>
      </div>
    )
  } else if (!characteristics.data || !categories.data) {
    axesBody = <span className="ui-field__hint">Загружаем характеристики…</span>
  } else {
    axesBody = (
      <>
        {shownAxes.length > 0 ? (
          <div className="axes-field__options">
            {shownAxes.map((characteristic) => {
              const unavailable = !available(characteristic)
              return (
                <label
                  key={characteristic.id}
                  className={unavailable ? 'axes-field__option axes-field__option--unavailable' : 'axes-field__option'}
                  title={unavailable ? 'Недоступна в выбранной категории' : undefined}
                >
                  <input
                    type="checkbox"
                    checked={axisIds.includes(characteristic.id)}
                    onChange={(event) => toggle(characteristic.id, event.target.checked)}
                  />
                  {characteristic.name}
                  {unavailable && <span className="category-note">нет в категории</span>}
                </label>
              )
            })}
          </div>
        ) : (
          <span className="ui-field__hint">В этой категории пока нет характеристик — заведите новую.</span>
        )}
        {addingAxis ? (
          <InlineCreateField
            label="Название новой характеристики"
            placeholder="Например: Цвет"
            field="name"
            // Новая — в категории группы, чтобы сразу подошла в оси
            create={(text) => adminApi.createCharacteristic({ name: text, category_id: categoryId })}
            onCreated={(created) => {
              characteristics.mutate((list) => withCharacteristic(list, created))
              setAxisIds((ids) => [...ids, created.id])
              setAddingAxis(false)
            }}
            onCancel={() => setAddingAxis(false)}
          />
        ) : (
          <Button variant="text" className="axes-field__add" onClick={() => setAddingAxis(true)}>
            + Новая характеристика
          </Button>
        )}
      </>
    )
  }

  return (
    <Dialog
      title={group ? 'Группа вариантов' : 'Новая группа вариантов'}
      onClose={onClose}
      actions={
        <>
          <Button variant="text" onClick={onClose}>
            Отмена
          </Button>
          <Button type="submit" form={FORM_ID} variant="primary" disabled={saving}>
            {saving ? 'Сохраняем…' : group ? 'Сохранить' : 'Создать группу'}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} className="ui-form" onSubmit={handleSubmit} noValidate>
        <FieldError messages={errors.non_field_errors} />
        <Field
          label="Название"
          errors={errors.name}
          hint="Модель без цвета и памяти: «iPhone 16 Pro». Покупатели его не видят — только вы."
        >
          <input
            className="ui-input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            aria-invalid={Boolean(errors.name)}
            maxLength={255}
            data-autofocus
          />
        </Field>

        <Field
          label="Категория"
          errors={errors.category_id}
          hint="Товары группы лежат в ней или в её подкатегориях. Без категории — различаются только по общим характеристикам."
        >
          <CategorySelect
            categories={categories}
            value={categoryId}
            onChange={setCategoryId}
            emptyLabel="Без категории"
            invalid={Boolean(errors.category_id)}
          />
        </Field>

        <fieldset className="axes-field" aria-invalid={Boolean(errors.axis_ids)}>
          <legend className="ui-field__label">Различаются по</legend>
          {axesBody}
          {errors.axis_ids ? (
            <FieldError messages={errors.axis_ids} />
          ) : (
            <span className="ui-field__hint">
              На витрине у каждой — своя строка кнопок. Значения этих характеристик нужны всем товарам группы.
            </span>
          )}
        </fieldset>
      </form>
    </Dialog>
  )
}
