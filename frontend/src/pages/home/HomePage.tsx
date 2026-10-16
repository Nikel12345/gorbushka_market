import { ProductCatalog } from '@/features/product-catalog'

/** Главная: лента товаров всех магазинов. Фильтры слева, поиск — в шапке (тот же ?q=), реклама между строками. */
export function HomePage() {
  return (
    <ProductCatalog
      title="Все товары"
      emptyText="Загляните позже — магазины скоро что-нибудь выставят."
      withPromo
    />
  )
}
