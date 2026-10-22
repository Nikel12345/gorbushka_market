// Дерево категорий в админке витрины: загрузка и обход плоского списка (родитель, затем его подкатегории)
import { adminApi, type Category, type CategoryBrief } from '@/shared/api'
import { useRequest } from '@/shared/lib'

const loadCategories = (signal: AbortSignal) => adminApi.listCategories({ signal })

/**
 * Все категории в порядке дерева. После правок — reload, а не mutate: порядок, уровни
 * и счётчики товаров считает сервер.
 */
export function useCategories() {
  return useRequest(loadCategories)
}

export type CategoriesRequest = ReturnType<typeof useCategories>

/** Категория и все её подкатегории: в списке они идут сразу за ней, с уровнем глубже */
export function subtreeIds(list: Category[], id: number): Set<number> {
  const ids = new Set<number>()
  const start = list.findIndex((category) => category.id === id)
  if (start === -1) return ids
  ids.add(id)
  for (let i = start + 1; i < list.length && list[i].depth > list[start].depth; i++) ids.add(list[i].id)
  return ids
}

/** Путь от верхнего уровня до категории; неизвестная — пустой */
export function categoryPath(list: Category[], id: number): Category[] {
  const byId = new Map(list.map((category) => [category.id, category]))
  const path: Category[] = []
  let current = byId.get(id)
  // Ограничение длины — на случай устаревшего списка с циклом
  while (current && path.length < list.length) {
    path.unshift(current)
    current = current.parent_id === null ? undefined : byId.get(current.parent_id)
  }
  return path
}

/** «Электроника / Смартфоны»; категории нет в списке — её собственное название */
export function categoryPathLabel(list: Category[], category: CategoryBrief): string {
  const path = categoryPath(list, category.id)
  return path.length > 0 ? path.map((item) => item.name).join(' / ') : category.name
}

/**
 * Доступно ли привязанное к категории bound (характеристика, группа) товару категории categoryId:
 * без привязки — везде, иначе — в этой категории и её подкатегориях. Товару без категории — только общее.
 */
export function isAvailableIn(list: Category[], bound: CategoryBrief | null, categoryId: number | null): boolean {
  if (bound === null) return true
  if (categoryId === null) return false
  return categoryPath(list, categoryId).some((category) => category.id === bound.id)
}
