import { ProductCatalog } from '@/features/product-catalog'

/** Главная: каталог товаров. Фильтры слева, поиск — в шапке (тот же ?q=), реклама между строками. */
export function HomePage() {
  return <ProductCatalog title="Все товары" emptyText="Загляните позже — скоро здесь появятся товары." withPromo />
}
