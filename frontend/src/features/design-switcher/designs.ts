/**
 * Варианты дизайна витрины. Стили вариантов — app/styles/designs.css (селектор :root[data-design='…']).
 * swatch — два цвета кружка в переключателе: фон и акцент варианта.
 */
export const designs = [
  { id: 'clean', title: 'Чистый', swatch: ['#ffffff', '#bc0032'] },
  { id: 'market', title: 'Рынок', swatch: ['#ffd400', '#bc0032'] },
  { id: 'dark', title: 'Тёмный', swatch: ['#1b1b1f', '#e0245a'] },
  { id: 'aurora', title: 'Аврора', swatch: ['#efe6ff', '#ff3d6e'] },
] as const

export type DesignId = (typeof designs)[number]['id']

export const DEFAULT_DESIGN: DesignId = 'clean'

export function isDesignId(value: unknown): value is DesignId {
  return designs.some((design) => design.id === value)
}
