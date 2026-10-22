import { useState, type FormEvent } from 'react'
import { adminApi, getFieldErrors, type Characteristic, type CharacteristicPayload, type FieldErrors } from '@/shared/api'
import { Button, Dialog, Field, FieldError } from '@/shared/ui'
import type { CategoriesRequest } from './categories'
import { CategorySelect } from './CategorySelect'

const FORM_ID = 'characteristic-form'

interface CharacteristicFormDialogProps {
  /** Нет — новая характеристика */
  characteristic?: Characteristic
  categories: CategoriesRequest
  onClose: () => void
  onSaved: (characteristic: Characteristic) => void
}

/** Название характеристики, где она доступна (категория с подкатегориями или все) и её место в карточке. */
export function CharacteristicFormDialog({ characteristic, categories, onClose, onSaved }: CharacteristicFormDialogProps) {
  const [name, setName] = useState(characteristic?.name ?? '')
  const [categoryId, setCategoryId] = useState<number | null>(characteristic?.category?.id ?? null)
  const [sortOrder, setSortOrder] = useState(characteristic ? String(characteristic.sort_order) : '')
  const [errors, setErrors] = useState<FieldErrors>({})
  const [saving, setSaving] = useState(false)

  const moved = characteristic !== undefined && categoryId !== (characteristic.category?.id ?? null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const localErrors: FieldErrors = {}
    if (!name.trim()) localErrors.name = ['Введите название.']
    if (sortOrder.trim() && !/^\d{1,4}$/.test(sortOrder.trim())) localErrors.sort_order = ['Целое число от 0 до 9999.']
    setErrors(localErrors)
    if (Object.keys(localErrors).length > 0) return

    const payload: CharacteristicPayload = { name: name.trim(), category_id: categoryId }
    if (sortOrder.trim()) payload.sort_order = Number(sortOrder)

    setSaving(true)
    try {
      onSaved(
        characteristic
          ? await adminApi.updateCharacteristic(characteristic.id, payload)
          : await adminApi.createCharacteristic(payload),
      )
    } catch (error) {
      setErrors(getFieldErrors(error))
      setSaving(false)
    }
  }

  return (
    <Dialog
      title={characteristic ? 'Характеристика' : 'Новая характеристика'}
      onClose={onClose}
      actions={
        <>
          <Button variant="text" onClick={onClose}>
            Отмена
          </Button>
          <Button type="submit" form={FORM_ID} variant="primary" disabled={saving}>
            {saving ? 'Сохраняем…' : characteristic ? 'Сохранить' : 'Создать'}
          </Button>
        </>
      }
    >
      <form id={FORM_ID} className="ui-form" onSubmit={handleSubmit} noValidate>
        <FieldError messages={errors.non_field_errors} />
        <Field label="Название" errors={errors.name} hint="Как в карточке товара: «Цвет», «Встроенная память».">
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
          label="Где доступна"
          errors={errors.category_id}
          hint={
            moved
              ? 'Товары, где она станет недоступна, перестанут её показывать — их нужно будет поправить.'
              : 'В выбранной категории и всех её подкатегориях. «Цвет» лучше оставить общим, «Встроенную память» — привязать к «Смартфонам».'
          }
        >
          <CategorySelect
            categories={categories}
            value={categoryId}
            onChange={setCategoryId}
            emptyLabel="Во всех категориях"
            invalid={Boolean(errors.category_id)}
          />
        </Field>
        <Field
          label="Порядок"
          errors={errors.sort_order}
          hint="Чем меньше, тем выше строка в карточке товара и в кнопках вариантов."
        >
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
