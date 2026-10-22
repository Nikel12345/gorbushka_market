import { apiRequest, type ApiRequestInit } from './client'
import type { DeliveryMethod } from './delivery'
import { productFilterQuery, type ProductFilterParams } from './productFilters'
import { withQuery } from './query'
import type { ProductPhoto, ShopBrief } from './admin'
import type { CursorPage } from './types'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

/** Товар в публичной ленте (ProductCardSerializer) */
export interface ProductCard {
  id: number
  title: string
  /** Денежные поля приходят строкой ("79990.00") */
  price: string
  /** URL фото, null — фото нет, показывается заглушка */
  image: string | null
  in_stock: boolean
  shop: ShopBrief
  /** Средняя оценка по отзывам строкой ("4.75"); "0.00" — отзывов нет */
  rating: string
  reviews_count: number
  created_at: string
}

/** Страница товара (ProductPublicDetailSerializer) */
export interface ProductDetail extends ProductCard {
  description: string
  quantity: number
  /** Все фото по порядку, первое — обложка (image) */
  images: ProductPhoto[]
  /** Как можно получить товар */
  delivery_methods: DeliveryMethod[]
  characteristics: ProductCharacteristic[]
  /** Строка на каждую характеристику, по которой различаются варианты. Пусто — вариантов нет */
  variants: ProductVariantRow[]
}

/** Характеристика товара: «Цвет: Синий» (ProductCharacteristicSerializer) */
export interface ProductCharacteristic {
  characteristic_id: number
  name: string
  value_id: number
  value: string
  /**
   * false — характеристика недоступна в категории товара (категории или характеристику перенесли).
   * На витрине такие не приходят, в админке их нужно поправить.
   */
  in_category: boolean
}

/** Категория в товаре, характеристике, группе (CategoryBriefSerializer) */
export interface CategoryBrief {
  id: number
  name: string
  /** Часть адреса раздела; при переименовании не меняется */
  slug: string
}

/**
 * Категория в плоском списке дерева (CategorySerializer): родитель, затем его подкатегории
 * по sort_order и названию. Вложенность собирается по parent_id.
 */
export interface Category extends CategoryBrief {
  /** null — верхний уровень */
  parent_id: number | null
  sort_order: number
  /** Уровень: верхний — 0 */
  depth: number
  /** Товаров на продаже вместе с подкатегориями */
  products_count: number
}

/** Варианты по одной характеристике (catalog/variants.py: variant_options) */
export interface ProductVariantRow {
  characteristic_id: number
  name: string
  options: ProductVariantOption[]
}

/** Значение характеристики и товар группы, на который ведёт его кнопка */
export interface ProductVariantOption {
  value_id: number
  value: string
  product_id: number
  /** Значение текущего товара */
  selected: boolean
  /** false — товара с этим значением и остальными как у текущего нет, ведёт на ближайший */
  exact: boolean
  in_stock: boolean
}

/** Сортировки ленты (ProductFeedPagination.sort_options) */
export const PRODUCT_SORTS = ['new', 'price_asc', 'price_desc'] as const
export type ProductSort = (typeof PRODUCT_SORTS)[number]

export interface ProductFeedParams extends ProductFilterParams {
  /** Только товары одного магазина — для страницы магазина */
  shop?: number
  sort?: ProductSort
  /** Позиция из next_cursor предыдущей порции; без него — с начала */
  cursor?: string
}

export const catalogApi = {
  feed: ({ shop, sort, cursor, ...filters }: ProductFeedParams = {}, options?: RequestOptions) =>
    apiRequest<CursorPage<ProductCard>>(
      withQuery('/catalog/products/', { ...productFilterQuery(filters), shop, sort, cursor }),
      options,
    ),

  /** 404 — товара нет или он снят с продажи */
  getProduct: (id: number, options?: RequestOptions) => apiRequest<ProductDetail>(`/catalog/products/${id}/`, options),

  /**
   * «С этим товаром часто покупают»: до 5 товаров на продаже, сначала самые частые.
   * Пусто — данных пока нет; другие варианты того же товара сюда не попадают.
   */
  boughtTogether: (id: number, options?: RequestOptions) =>
    apiRequest<ProductCard[]>(`/catalog/products/${id}/bought-together/`, options),
}
