import { isShowcaseDesign, useCurrentDesign } from '@/features/design-switcher'
import { ShowcaseProductPage } from '@/features/storefront'
import { ProductPage } from './ProductPage'

/** Страница товара: у «витринных» вариантов дизайна — своя раскладка по макету */
export function ProductRoute() {
  const design = useCurrentDesign()
  return isShowcaseDesign(design) ? <ShowcaseProductPage design={design} /> : <ProductPage />
}
