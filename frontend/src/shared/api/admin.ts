import type { Category, CategoryBrief, ProductCharacteristic } from './catalog'
import { apiRequest, type ApiRequestInit } from './client'
import type { DeliveryMethod } from './delivery'
import { toFormData } from './formData'
import type { PaymentMethodCode, PaymentStatus, ShipmentBrief } from './purchases'
import { productFilterQuery, type ProductFilterParams } from './productFilters'
import { withQuery } from './query'
import type { Paginated } from './types'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

// Админка магазина: /admin/... Доступ — только сотрудники (is_staff), остальным 403.
// Магазин один, поэтому его id в путях нет.

// --- Магазин ---

export interface ShopBrief {
  id: number
  name: string
}

/** Магазин в админке (ShopAdminSerializer). 404 shop_not_found — магазин ещё не заведён. */
export interface Shop extends ShopBrief {
  description: string
  /** Где забирать товар при самовывозе: павильон, ряд, место. Пусто — самовывоз недоступен. */
  address: string
  /** Товаров на продаже */
  products_count: number
  created_at: string
  updated_at: string
}

export interface ShopPayload {
  name: string
  description?: string
  address?: string
}

// --- Товары ---

export type ProductStatus = 'active' | 'archived'

/** Фото товара (ProductImageSerializer) */
export interface ProductPhoto {
  id: number
  /** null — файл недоступен */
  url: string | null
}

/** Сколько фото можно у товара (PRODUCT_IMAGES_MAX на бэке; точную проверку делает сервер) */
export const PRODUCT_PHOTOS_MAX = 10

/** Товар в админке (ProductAdminSerializer) */
export interface Product {
  id: number
  title: string
  description: string
  /** Цена в долларах — так она хранится и так её задаёт магазин. Денежные поля приходят строкой ("965.04") */
  price_usd: string
  /** Она же в рублях по текущему курсу ЦБ — столько видит и платит покупатель */
  price: string
  quantity: number
  /** Обложка — первое из images (локально относительный /media/...), null — фото нет */
  image: string | null
  /** Все фото по порядку, первое — обложка */
  images: ProductPhoto[]
  delivery_methods: DeliveryMethod[]
  /** null — товар не разложен по категориям: есть в общей ленте, но ни в одном разделе */
  category: CategoryBrief | null
  /** Группа вариантов; null — товар сам по себе */
  group: ProductGroupBrief | null
  characteristics: ProductCharacteristic[]
  status: ProductStatus
  status_display: string
  created_at: string
  updated_at: string
}

/** Поля товара, которые задаёт магазин (кроме фото) */
export interface ProductFieldsPayload {
  title: string
  /** В долларах; в рубли переводит сервер по курсу ЦБ */
  price_usd: string
  quantity?: number
  description?: string
  /** Хотя бы один способ; самовывоз — только если у магазина указан адрес */
  delivery_method_ids: number[]
  /** null — убрать из категории. Характеристики и группа товара должны быть доступны в ней */
  category_id?: number | null
  /** null — убрать из группы */
  group_id?: number | null
  /**
   * По одному значению на характеристику; заменяет набор целиком. Только характеристики, доступные
   * в категории товара; в группе — обязательно все её оси
   */
  characteristic_value_ids?: number[]
}

export interface ProductCreatePayload extends ProductFieldsPayload {
  /** Фото по порядку, первое станет обложкой */
  images?: File[]
}

/** images — новые фото, добавляются в конец; удаление и порядок — отдельными запросами */
export type ProductUpdatePayload = Partial<ProductFieldsPayload> & { images?: File[] }

export interface ProductListParams extends ProductFilterParams {
  page?: number
  /** Только товары этой группы вариантов */
  group?: number
}

// --- Категории ---

export interface CategoryPayload {
  name: string
  /** null — верхний уровень. Перенос — куда угодно, кроме самой категории и её подкатегорий */
  parent_id?: number | null
  /** Не передан при создании — генерируется из названия */
  slug?: string
  sort_order?: number
}

// --- Характеристики и группы вариантов ---
// Удаление характеристик и правка значений — пока только в админке Django: значения уже стоят у товаров.

export interface CharacteristicValue {
  id: number
  value: string
  sort_order: number
}

/** Характеристика со справочником значений (CharacteristicSerializer) */
export interface Characteristic {
  id: number
  name: string
  /** Где доступна: в этой категории и её подкатегориях. null — во всех категориях */
  category: CategoryBrief | null
  sort_order: number
  values: CharacteristicValue[]
}

export interface CharacteristicPayload {
  /** Уникально в ветке: среди общих, категорий выше, самой категории и её подкатегорий */
  name: string
  /** null — во всех категориях. Перенос товары не проверяет: где стала недоступна — скрывается */
  category_id?: number | null
  sort_order?: number
}

export interface CharacteristicBrief {
  id: number
  name: string
}

export interface ProductGroupBrief {
  id: number
  name: string
}

/** Группа вариантов: товары одной модели, которые различаются значениями осей (цвет, память) */
export interface ProductGroup extends ProductGroupBrief {
  /** Где лежат товары группы (с подкатегориями); null — где угодно, но оси только общие */
  category: CategoryBrief | null
  axes: CharacteristicBrief[]
}

export interface ProductGroupPayload {
  name: string
  /** Все товары группы на продаже должны лежать в ней */
  category_id?: number | null
  /** Хотя бы одна, из доступных в категории группы; новые оси должны быть заполнены у всех товаров группы */
  axis_ids: number[]
}

export interface GroupListParams {
  page?: number
  /** Поиск по названию */
  q?: string
  /** Только подходящие товарам категории: без категории, этой категории и категорий выше */
  category?: number
}

// --- Заказы ---

/** ready — «готов к выдаче» (самовывоз) или «передан курьеру» (курьерская доставка) */
export type OrderStatus = 'new' | 'confirmed' | 'ready' | 'completed' | 'cancelled'

/** Куда текущий участник может перевести заказ — кнопки действий */
export interface OrderStatusOption {
  status: OrderStatus
  /** Название статуса с учётом доставки: «Готов к выдаче», «Передан курьеру»… */
  name: string
}

export interface OrderBuyer {
  id: number
  email: string
  first_name: string
  last_name: string
}

export interface OrderItem {
  id: number
  product_id: number
  title: string
  /** Текущее фото товара; null — нет фото */
  image: string | null
  price: string
  quantity: number
  total: string
  /** Устарело: доставка теперь у заказа (Order.shipment) */
  shipment: ShipmentBrief | null
}

/** Общая часть заказа для всех сторон (OrderSerializer). Заказ — магазин × способ доставки. */
export interface OrderBase {
  id: number
  status: OrderStatus
  /** Название зависит от доставки: «Готов к выдаче» / «Передан курьеру», «Выдан» / «Доставлен» */
  status_display: string
  available_statuses: OrderStatusOption[]
  /** Товары магазина, без доставки */
  total_amount: string
  /** Из суммы заказа оплачено бонусами */
  bonus_amount: string
  /** Сколько взять с покупателя при выдаче (только оплата при получении, иначе 0) */
  amount_due: string
  /** null — у заказов, оформленных до появления доставки */
  shipment: ShipmentBrief | null
  items: OrderItem[]
  created_at: string
  updated_at: string
}

export interface OrderPayment {
  method: PaymentMethodCode
  method_display: string
  status: PaymentStatus
  status_display: string
}

/** Заказ в админке (OrderAdminSerializer) */
export interface Order extends OrderBase {
  buyer: OrderBuyer
  /** Покупка, частью которой является заказ; null — у старых заказов */
  purchase_id: number | null
  /** Оплата покупки; null — у старых заказов */
  payment: OrderPayment | null
  /** Комментарий покупателя к покупке */
  comment: string
}

export interface OrderListParams {
  page?: number
  status?: OrderStatus
}

export const adminApi = {
  getShop: (options?: RequestOptions) => apiRequest<Shop>('/admin/shop/', options),

  updateShop: (payload: Partial<ShopPayload>) => apiRequest<Shop>('/admin/shop/', { method: 'PATCH', json: payload }),

  listProducts: ({ page, group, ...filters }: ProductListParams = {}, options?: RequestOptions) =>
    apiRequest<Paginated<Product>>(
      withQuery('/admin/products/', { page, group, ...productFilterQuery(filters) }),
      options,
    ),

  getProduct: (productId: number, options?: RequestOptions) =>
    apiRequest<Product>(`/admin/products/${productId}/`, options),

  /** multipart: вместе с полями уходят файлы фото */
  createProduct: (payload: ProductCreatePayload) =>
    apiRequest<Product>('/admin/products/', { method: 'POST', body: toFormData(payload) }),

  /**
   * Изменить товар. Переданные delivery_method_ids и characteristic_value_ids заменяют набор целиком.
   * С новыми фото уходит multipart — в нём не передать null и пустой список, поэтому поля и фото
   * лучше сохранять отдельными запросами (см. saveProductWithPhotos).
   */
  updateProduct: (productId: number, payload: ProductUpdatePayload) =>
    apiRequest<Product>(
      `/admin/products/${productId}/`,
      payload.images?.length
        ? { method: 'PATCH', body: toFormData(payload) }
        : { method: 'PATCH', json: { ...payload, images: undefined } },
    ),

  /** Удалить фото; если это была обложка, ей станет следующее */
  deleteProductPhoto: (productId: number, photoId: number) =>
    apiRequest<null>(`/admin/products/${productId}/images/${photoId}/`, { method: 'DELETE' }),

  /** Новый порядок всех фото товара (первое станет обложкой) */
  reorderProductPhotos: (productId: number, ids: number[]) =>
    apiRequest<ProductPhoto[]>(`/admin/products/${productId}/images/order/`, { method: 'PUT', json: { ids } }),

  /** Снять с продажи (мягкое удаление на бэке) */
  archiveProduct: (productId: number) => apiRequest<null>(`/admin/products/${productId}/`, { method: 'DELETE' }),

  /** Все категории плоским списком в порядке дерева (без пагинации) */
  listCategories: (options?: RequestOptions) => apiRequest<Category[]>('/admin/categories/', options),

  createCategory: (payload: CategoryPayload) =>
    apiRequest<Category>('/admin/categories/', { method: 'POST', json: payload }),

  /** В том числе перенос (parent_id); в цикл — 400 category_cycle */
  updateCategory: (categoryId: number, payload: Partial<CategoryPayload>) =>
    apiRequest<Category>(`/admin/categories/${categoryId}/`, { method: 'PATCH', json: payload }),

  /** Только пустую: без подкатегорий, характеристик, групп и товаров на продаже — иначе 400 category_not_empty */
  deleteCategory: (categoryId: number) =>
    apiRequest<null>(`/admin/categories/${categoryId}/`, { method: 'DELETE' }),

  /** Все характеристики со справочниками значений (без пагинации) */
  listCharacteristics: (options?: RequestOptions) =>
    apiRequest<Characteristic[]>('/admin/characteristics/', options),

  createCharacteristic: (payload: CharacteristicPayload) =>
    apiRequest<Characteristic>('/admin/characteristics/', { method: 'POST', json: payload }),

  /** Название, категория (перенос), порядок */
  updateCharacteristic: (characteristicId: number, payload: Partial<CharacteristicPayload>) =>
    apiRequest<Characteristic>(`/admin/characteristics/${characteristicId}/`, { method: 'PATCH', json: payload }),

  /** Новое значение в справочник («Розовый» для «Цвет»). «черный» при «Чёрный» — 400 */
  createCharacteristicValue: (characteristicId: number, payload: { value: string }) =>
    apiRequest<CharacteristicValue>(`/admin/characteristics/${characteristicId}/values/`, {
      method: 'POST',
      json: payload,
    }),

  listGroups: ({ page, q, category }: GroupListParams = {}, options?: RequestOptions) =>
    apiRequest<Paginated<ProductGroup>>(withQuery('/admin/product-groups/', { page, q, category }), options),

  getGroup: (groupId: number, options?: RequestOptions) =>
    apiRequest<ProductGroup>(`/admin/product-groups/${groupId}/`, options),

  createGroup: (payload: ProductGroupPayload) =>
    apiRequest<ProductGroup>('/admin/product-groups/', { method: 'POST', json: payload }),

  /** Товары группы — listProducts({ group }) */
  updateGroup: (groupId: number, payload: Partial<ProductGroupPayload>) =>
    apiRequest<ProductGroup>(`/admin/product-groups/${groupId}/`, { method: 'PATCH', json: payload }),

  listOrders: (params: OrderListParams = {}, options?: RequestOptions) =>
    apiRequest<Paginated<Order>>(withQuery('/admin/orders/', { page: params.page, status: params.status }), options),

  /** Перевести заказ в статус из available_statuses; ответ — заказ с новыми действиями */
  changeOrderStatus: (orderId: number, status: OrderStatus) =>
    apiRequest<Order>(`/admin/orders/${orderId}/status/`, { method: 'POST', json: { status } }),
}
