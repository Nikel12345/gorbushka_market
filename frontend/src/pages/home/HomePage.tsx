import { useSearchParams } from 'react-router'
import { isShowcaseDesign, useCurrentDesign } from '@/features/design-switcher'
import { ProductCatalog } from '@/features/product-catalog'
import { hasCatalogFilters, ShowcaseCatalog, useCategories } from '@/features/storefront'

/** Заголовок ленты «витринных» вариантов без фильтров — как в их макетах */
const SHOWCASE_TITLES = { vitrina: 'Новинки', night: 'Каталог', afisha: 'Новинки' } as const

/**
 * Главная: каталог товаров. Фильтры слева, поиск — в шапке (тот же ?q=), реклама между строками.
 * Выбрана категория (полоса категорий под шапкой) — её название в заголовке.
 * «Витринные» варианты дизайна показывают свою ленту (фильтры чипсами или своей панелью).
 */
export function HomePage() {
  const design = useCurrentDesign()
  const [searchParams] = useSearchParams()
  const categories = useCategories()
  const categoryId = Number(searchParams.get('category'))
  const category = categoryId ? categories.find((item) => item.id === categoryId) : undefined

  if (isShowcaseDesign(design)) {
    const q = searchParams.get('q')
    const filtered = hasCatalogFilters(searchParams)
    const title = q ? `Поиск: «${q}»` : (category?.name ?? (filtered ? 'Все товары' : SHOWCASE_TITLES[design]))
    return <ShowcaseCatalog design={design} title={title} heading={filtered ? 'h1' : 'h2'} />
  }

  return (
    <ProductCatalog
      title={category?.name ?? 'Все товары'}
      emptyText="Загляните позже — скоро здесь появятся товары."
      withPromo
    />
  )
}
