/**
 * Варианты дизайна витрины. Стили вариантов — app/styles/designs.css и designs-showcase.css
 * (селектор :root[data-design='…']).
 * swatch — два цвета кружка в переключателе: фон и акцент варианта.
 */
export const designs = [
  { id: 'aurora', title: 'Аврора', swatch: ['#efe6ff', '#ff3d6e'] },
  { id: 'vitrina', title: 'Витрина', swatch: ['#ffffff', '#111114'] },
  { id: 'night', title: 'Ночь', swatch: ['#0b0b0d', '#ff4d73'] },
  { id: 'afisha', title: 'Афиша', swatch: ['#bc0032', '#0d0d0d'] },
] as const

export type DesignId = (typeof designs)[number]['id']

/** Вариант для тех, кто ещё не выбирал (и у кого сохранён убранный вариант: «Чистый», «Рынок», «Тёмный») */
export const DEFAULT_DESIGN: DesignId = 'vitrina'

export function isDesignId(value: unknown): value is DesignId {
  return designs.some((design) => design.id === value)
}

/**
 * Варианты со своей главной: первый экран, промо-блоки, категории и блок о магазине
 * (features/storefront), полоса категорий под шапкой. Остальные варианты меняют только стиль.
 */
export const SHOWCASE_DESIGNS = ['vitrina', 'night', 'afisha'] as const satisfies readonly DesignId[]

export type ShowcaseDesignId = (typeof SHOWCASE_DESIGNS)[number]

export function isShowcaseDesign(design: DesignId): design is ShowcaseDesignId {
  return (SHOWCASE_DESIGNS as readonly DesignId[]).includes(design)
}
