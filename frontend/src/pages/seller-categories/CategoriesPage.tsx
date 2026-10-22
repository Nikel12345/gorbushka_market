import { useState, type CSSProperties } from 'react'
import { Link } from 'react-router'
import { useCategories, useCharacteristics } from '@/features/seller'
import { adminApi, getErrorMessage, type Category, type Characteristic } from '@/shared/api'
import { pluralize } from '@/shared/lib'
import { Button, Card, Dialog, EmptyState, ErrorState, FieldError, LinearProgress, Loader, PageHeader } from '@/shared/ui'
import { CategoryFormDialog } from './CategoryFormDialog'
import './CategoriesPage.css'

const CATEGORY_WORDS: [string, string, string] = ['категория', 'категории', 'категорий']
const PRODUCT_WORDS: [string, string, string] = ['товар', 'товара', 'товаров']

type FormState = { category: Category } | { parentId: number | null }

/**
 * Дерево категорий каталога: подкатегории под родителем, у каждой — товары на продаже и привязанные
 * к ней характеристики. Добавить, переименовать, перенести, удалить пустую.
 */
export function CategoriesPage() {
  const categories = useCategories()
  const characteristics = useCharacteristics()
  const [form, setForm] = useState<FormState | null>(null)
  const [deleting, setDeleting] = useState<Category | null>(null)

  // Привязанные к самой категории (без унаследованных сверху)
  const bound = new Map<number, Characteristic[]>()
  for (const characteristic of characteristics.data ?? []) {
    if (!characteristic.category) continue
    const list = bound.get(characteristic.category.id) ?? []
    list.push(characteristic)
    bound.set(characteristic.category.id, list)
  }

  let content
  if (categories.status === 'error' && !categories.data) {
    content = <ErrorState message={getErrorMessage(categories.error)} onRetry={categories.reload} />
  } else if (!categories.data) {
    content = <Loader />
  } else if (categories.data.length === 0) {
    content = (
      <EmptyState
        title="Категорий пока нет"
        text="Начните с разделов верхнего уровня — «Смартфоны», «Ноутбуки», — а подкатегории добавите в них."
        action={
          <Button variant="primary" onClick={() => setForm({ parentId: null })}>
            Добавить категорию
          </Button>
        }
      />
    )
  } else {
    content = (
      <ul className="categories-list">
        {categories.data.map((category) => (
          <CategoryItem
            key={category.id}
            category={category}
            characteristics={bound.get(category.id) ?? []}
            onAdd={() => setForm({ parentId: category.id })}
            onEdit={() => setForm({ category })}
            onDelete={() => setDeleting(category)}
          />
        ))}
      </ul>
    )
  }

  function handleChanged() {
    setForm(null)
    setDeleting(null)
    categories.reload()
  }

  return (
    <>
      <PageHeader
        title="Категории"
        subtitle={
          categories.data
            ? pluralize(categories.data.length, CATEGORY_WORDS)
            : 'Разделы каталога: в них лежат товары, к ним привязаны характеристики и группы'
        }
        actions={
          <Button variant="primary" onClick={() => setForm({ parentId: null })}>
            + Категория
          </Button>
        }
      />

      <Card flush>
        <div className="categories">
          {categories.status === 'loading' && categories.data && <LinearProgress />}
          {content}
        </div>
      </Card>

      <p className="categories-hint">
        Раздел показывает товары вместе с подкатегориями, а характеристики категории доступны и в её подкатегориях.
        Перенос ничего не блокирует: что станет товару недоступно, скроется с витрины, а в карточке товара будет
        отмечено.
      </p>

      {form && (
        <CategoryFormDialog
          category={'category' in form ? form.category : undefined}
          parentId={'parentId' in form ? form.parentId : undefined}
          categories={categories}
          onClose={() => setForm(null)}
          onSaved={handleChanged}
        />
      )}

      {deleting && (
        <DeleteCategoryDialog category={deleting} onClose={() => setDeleting(null)} onDeleted={handleChanged} />
      )}
    </>
  )
}

function CategoryItem({
  category,
  characteristics,
  onAdd,
  onEdit,
  onDelete,
}: {
  category: Category
  characteristics: Characteristic[]
  onAdd: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const style = { '--depth': category.depth } as CSSProperties

  return (
    <li className={category.depth === 0 ? 'categories-list__item categories-list__item--root' : 'categories-list__item'} style={style}>
      <div className="categories-list__main">
        <span className="categories-list__name">{category.name}</span>
        <span className="categories-list__meta">
          {category.products_count > 0 ? (
            <Link to={`/seller/products?category=${category.id}`}>
              {pluralize(category.products_count, PRODUCT_WORDS)}
            </Link>
          ) : (
            'нет товаров'
          )}
          <span aria-hidden="true"> · </span>
          <span title="Адрес раздела">{category.slug}</span>
        </span>
        {characteristics.length > 0 && (
          <span className="categories-list__characteristics">
            Характеристики: {characteristics.map((item) => item.name).join(', ')}
          </span>
        )}
      </div>
      <div className="categories-list__actions">
        <Button variant="text" onClick={onAdd} title="Добавить подкатегорию">
          + Подкатегория
        </Button>
        <Button variant="text" onClick={onEdit}>
          Изменить
        </Button>
        <Button variant="text" onClick={onDelete}>
          Удалить
        </Button>
      </div>
    </li>
  )
}

/** Удалить можно только пустую — иначе сервер объяснит, что мешает */
function DeleteCategoryDialog({
  category,
  onClose,
  onDeleted,
}: {
  category: Category
  onClose: () => void
  onDeleted: () => void
}) {
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string[]>()

  async function handleDelete() {
    setDeleting(true)
    setError(undefined)
    try {
      await adminApi.deleteCategory(category.id)
      onDeleted()
    } catch (err) {
      setError([getErrorMessage(err)])
      setDeleting(false)
    }
  }

  return (
    <Dialog
      title="Удалить категорию?"
      onClose={onClose}
      actions={
        <>
          <Button variant="text" onClick={onClose}>
            Отмена
          </Button>
          <Button variant="danger" onClick={handleDelete} disabled={deleting}>
            {deleting ? 'Удаляем…' : 'Удалить'}
          </Button>
        </>
      }
    >
      <p className="categories-dialog__text">
        «{category.name}» пропадёт из каталога. Удалить можно только пустую категорию: без подкатегорий, товаров
        на продаже и привязанных характеристик и групп.
      </p>
      <FieldError messages={error} />
    </Dialog>
  )
}
