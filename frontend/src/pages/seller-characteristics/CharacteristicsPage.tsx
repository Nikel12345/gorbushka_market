import { useState } from 'react'
import {
  categoryPathLabel,
  CharacteristicFormDialog,
  InlineCreateField,
  useCategories,
  useCharacteristics,
  withCharacteristic,
  withUpdatedCharacteristic,
  withValue,
} from '@/features/seller'
import { adminApi, getErrorMessage, type Category, type Characteristic, type CharacteristicValue } from '@/shared/api'
import { pluralize } from '@/shared/lib'
import { Button, Card, Chip, EmptyState, ErrorState, Loader, PageHeader } from '@/shared/ui'
import './CharacteristicsPage.css'

const VALUE_WORDS: [string, string, string] = ['значение', 'значения', 'значений']

interface Section {
  /** null — общие, во всех категориях */
  categoryId: number | null
  title: string
  items: Characteristic[]
}

/**
 * Характеристики по месту привязки: сначала общие, потом по категориям в порядке дерева
 * (характеристика доступна в своей категории и всех подкатегориях).
 */
function toSections(characteristics: Characteristic[], categories: Category[]): Section[] {
  const order = new Map(categories.map((category, index) => [category.id, index]))
  const sections = new Map<number | null, Section>()
  for (const characteristic of characteristics) {
    const key = characteristic.category?.id ?? null
    let section = sections.get(key)
    if (!section) {
      section = {
        categoryId: key,
        title: characteristic.category ? categoryPathLabel(categories, characteristic.category) : 'Во всех категориях',
        items: [],
      }
      sections.set(key, section)
    }
    section.items.push(characteristic)
  }
  const position = (id: number | null) => (id === null ? -1 : (order.get(id) ?? categories.length))
  return [...sections.values()].sort((a, b) => position(a.categoryId) - position(b.categoryId))
}

/**
 * Справочник характеристик: цвет, память и т. п. со списками значений. Товарам значения
 * выбираются только отсюда — так «Чёрный» и «черный» не станут разными вариантами.
 */
export function CharacteristicsPage() {
  const characteristics = useCharacteristics()
  const categories = useCategories()
  const { mutate } = characteristics
  /** Открытая форма: характеристика — правка, true — новая */
  const [form, setForm] = useState<Characteristic | true | null>(null)

  let content
  const failed = characteristics.status === 'error' ? characteristics : categories.status === 'error' ? categories : null
  if (failed) {
    content = (
      <Card>
        <ErrorState message={getErrorMessage(failed.error)} onRetry={failed.reload} />
      </Card>
    )
  } else if (!characteristics.data || !categories.data) {
    content = (
      <Card>
        <Loader />
      </Card>
    )
  } else if (characteristics.data.length === 0) {
    content = (
      <Card>
        <EmptyState
          title="Характеристик пока нет"
          text="Заведите первую — например, «Цвет» или «Встроенная память»."
          action={
            <Button variant="primary" onClick={() => setForm(true)}>
              Добавить характеристику
            </Button>
          }
        />
      </Card>
    )
  } else {
    content = toSections(characteristics.data, categories.data).map((section) => (
      <Card key={section.categoryId ?? 'all'} title={section.title} flush>
        <ul className="characteristics-list">
          {section.items.map((characteristic) => (
            <CharacteristicItem
              key={characteristic.id}
              characteristic={characteristic}
              onEdit={() => setForm(characteristic)}
              onValueAdded={(value) => mutate((list) => withValue(list, characteristic.id, value))}
            />
          ))}
        </ul>
      </Card>
    ))
  }

  return (
    <>
      <PageHeader
        title="Характеристики"
        subtitle="Свойства товаров и их значения. По ним же различаются варианты в группах."
        actions={
          <Button variant="primary" onClick={() => setForm(true)}>
            + Характеристика
          </Button>
        }
      />

      {content}

      <p className="characteristics-hint">
        Характеристика категории доступна товарам этой категории и всех её подкатегорий. Удалить характеристику,
        переименовать или удалить значение пока можно только в админке Django: значения уже стоят у товаров.
      </p>

      {form && (
        <CharacteristicFormDialog
          characteristic={form === true ? undefined : form}
          categories={categories}
          onClose={() => setForm(null)}
          onSaved={(saved) => {
            mutate((list) => (form === true ? withCharacteristic(list, saved) : withUpdatedCharacteristic(list, saved)))
            setForm(null)
          }}
        />
      )}
    </>
  )
}

function CharacteristicItem({
  characteristic,
  onEdit,
  onValueAdded,
}: {
  characteristic: Characteristic
  onEdit: () => void
  onValueAdded: (value: CharacteristicValue) => void
}) {
  const [adding, setAdding] = useState(false)
  /** Растёт после каждого добавления — поле пересоздаётся пустым */
  const [added, setAdded] = useState(0)

  return (
    <li className="characteristics-list__item">
      <div className="characteristics-list__head">
        <span className="characteristics-list__name">{characteristic.name}</span>
        <span className="characteristics-list__count">{pluralize(characteristic.values.length, VALUE_WORDS)}</span>
        <button type="button" className="characteristics-list__edit" onClick={onEdit}>
          Изменить
        </button>
      </div>
      <div className="characteristics-list__values">
        {characteristic.values.map((value) => (
          <Chip key={value.id}>{value.value}</Chip>
        ))}
        {adding ? (
          <InlineCreateField
            key={added}
            label={`Новое значение характеристики «${characteristic.name}»`}
            placeholder="Новое значение"
            field="value"
            create={(text) => adminApi.createCharacteristicValue(characteristic.id, { value: text })}
            onCreated={(value) => {
              onValueAdded(value)
              // Обычно значения заводят пачкой — поле остаётся открытым для следующего
              setAdded((count) => count + 1)
            }}
            onCancel={() => setAdding(false)}
          />
        ) : (
          <button type="button" className="characteristics-list__add" onClick={() => setAdding(true)}>
            + значение
          </button>
        )}
      </div>
    </li>
  )
}
