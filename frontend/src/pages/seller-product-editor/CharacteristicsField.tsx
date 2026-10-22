import { useState } from 'react'
import {
  InlineCreateField,
  isAvailableIn,
  withCharacteristic,
  withValue,
  type CategoriesRequest,
  type CharacteristicsRequest,
} from '@/features/seller'
import { adminApi, getErrorMessage, type Characteristic, type CharacteristicBrief } from '@/shared/api'
import { Button, FieldError } from '@/shared/ui'
import { characteristicRows, type CharacteristicRow } from './productForm'

interface CharacteristicsFieldProps {
  rows: CharacteristicRow[]
  /** Оси группы товара: их строки обязательны и не убираются */
  axes: CharacteristicBrief[]
  characteristics: CharacteristicsRequest
  /** Категория товара: предлагаются только доступные в ней характеристики */
  categoryId: number | null
  categories: CategoriesRequest
  onChange: (rows: CharacteristicRow[]) => void
  errors?: string[]
}

/** Пункт в выпадающих списках: «создать новое» вместо выбора из справочника */
const CREATE = 'create'

/**
 * Характеристики товара: строка на характеристику, значение — из справочника. Предлагаются только
 * доступные в категории товара; ставшие недоступными (сменили категорию) отмечены — их нужно убрать.
 * Нет нужного значения или характеристики — заводится тут же, без ухода со страницы.
 */
export function CharacteristicsField({
  rows,
  axes,
  characteristics,
  categoryId,
  categories,
  onChange,
  errors,
}: CharacteristicsFieldProps) {
  const [addingValueTo, setAddingValueTo] = useState<number | null>(null)
  const [addingCharacteristic, setAddingCharacteristic] = useState(false)

  const failed = characteristics.status === 'error' ? characteristics : categories.status === 'error' ? categories : null
  if (failed && (!characteristics.data || !categories.data)) {
    return (
      <div className="group-picker group-picker--error">
        <span className="group-picker__info">Не удалось загрузить характеристики: {getErrorMessage(failed.error)}</span>
        <Button onClick={failed.reload}>Повторить</Button>
      </div>
    )
  }
  if (!characteristics.data || !categories.data) return <span className="ui-field__hint">Загружаем характеристики…</span>

  const categoryList = categories.data
  const available = (item: Characteristic) => isAvailableIn(categoryList, item.category, categoryId)
  const byId = new Map(characteristics.data.map((item) => [item.id, item]))
  const shown = characteristicRows(rows, axes)
  const used = new Set(shown.map(({ row }) => row.characteristicId))
  const unused = characteristics.data.filter((item) => !used.has(item.id) && available(item))

  function setValue(characteristicId: number, valueId: number | null) {
    const exists = rows.some((row) => row.characteristicId === characteristicId)
    onChange(
      exists
        ? rows.map((row) => (row.characteristicId === characteristicId ? { ...row, valueId } : row))
        : [...rows, { characteristicId, valueId }],
    )
  }

  const add = (characteristicId: number) => onChange([...rows, { characteristicId, valueId: null }])
  const remove = (characteristicId: number) => onChange(rows.filter((row) => row.characteristicId !== characteristicId))

  return (
    <div className="characteristics-field">
      {shown.length > 0 ? (
        <ul className="characteristics-field__rows">
          {shown.map(({ row, axis }) => {
            const characteristic = byId.get(row.characteristicId)
            // Характеристику могли удалить в админке Django, пока открыта страница
            if (!characteristic) return null
            const unavailable = !available(characteristic)
            return (
              <li
                key={characteristic.id}
                className={
                  unavailable
                    ? 'characteristics-field__row characteristics-field__row--unavailable'
                    : 'characteristics-field__row'
                }
              >
                <span className="characteristics-field__name">
                  {characteristic.name}
                  {axis && (
                    <span
                      className="characteristics-field__axis"
                      title="По ней различаются товары группы — значение обязательно"
                    >
                      вариант
                    </span>
                  )}
                  {unavailable && (
                    <span
                      className="category-note"
                      title="Недоступна в категории товара — уберите её или выберите другую категорию"
                    >
                      нет в категории
                    </span>
                  )}
                </span>

                {addingValueTo === characteristic.id ? (
                  <InlineCreateField
                    label={`Новое значение характеристики «${characteristic.name}»`}
                    placeholder="Новое значение"
                    field="value"
                    create={(text) => adminApi.createCharacteristicValue(characteristic.id, { value: text })}
                    onCreated={(value) => {
                      characteristics.mutate((list) => withValue(list, characteristic.id, value))
                      setValue(characteristic.id, value.id)
                      setAddingValueTo(null)
                    }}
                    onCancel={() => setAddingValueTo(null)}
                  />
                ) : (
                  <select
                    className="ui-input"
                    value={row.valueId ?? ''}
                    aria-label={characteristic.name}
                    aria-invalid={(unavailable || (axis && row.valueId === null)) && Boolean(errors?.length)}
                    onChange={(event) => {
                      const { value } = event.target
                      if (value === CREATE) setAddingValueTo(characteristic.id)
                      else setValue(characteristic.id, value ? Number(value) : null)
                    }}
                  >
                    <option value="">Не выбрано</option>
                    {characteristic.values.map((value) => (
                      <option key={value.id} value={value.id}>
                        {value.value}
                      </option>
                    ))}
                    <option value={CREATE}>+ Новое значение…</option>
                  </select>
                )}

                {!axis && (
                  <button
                    type="button"
                    className="characteristics-field__remove"
                    onClick={() => remove(characteristic.id)}
                    aria-label={`Убрать «${characteristic.name}»`}
                    title="Убрать"
                  >
                    ✕
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      ) : (
        <span className="ui-field__hint">Цвет, память и другие свойства товара — пока ни одного.</span>
      )}

      <FieldError messages={errors} />

      {addingCharacteristic ? (
        <InlineCreateField
          label="Название новой характеристики"
          placeholder="Например: Цвет"
          field="name"
          // Новая — в категории товара, чтобы сразу была ему доступна
          create={(text) => adminApi.createCharacteristic({ name: text, category_id: categoryId })}
          onCreated={(created) => {
            characteristics.mutate((list) => withCharacteristic(list, created))
            add(created.id)
            setAddingCharacteristic(false)
          }}
          onCancel={() => setAddingCharacteristic(false)}
        />
      ) : (
        <select
          className="ui-input characteristics-field__add"
          value=""
          aria-label="Добавить характеристику"
          onChange={(event) => {
            const { value } = event.target
            if (value === CREATE) setAddingCharacteristic(true)
            else if (value) add(Number(value))
          }}
        >
          <option value="">+ Добавить характеристику</option>
          {unused.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
          <option value={CREATE}>Новая характеристика…</option>
        </select>
      )}
    </div>
  )
}
