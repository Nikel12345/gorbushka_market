import type { User } from './auth'
import { apiRequest, type ApiRequestInit } from './client'
import type { DeliveryMethod } from './delivery'
import { toFormData } from './formData'
import type { PaymentMethodCode, PaymentStatus, ShipmentBrief } from './purchases'
import { productFilterQuery, type ProductFilterParams } from './productFilters'
import { withQuery } from './query'
import type { Paginated } from './types'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

// --- Магазины и профиль ---

export interface ShopBrief {
  id: number
  name: string
}

/** Магазин в кабинете продавца (SellerShopSerializer) */
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

export interface SellerProfile extends User {
  shops: ShopBrief[]
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

export interface Product {
  id: number
  shop: ShopBrief
  title: string
  description: string
  /** Денежные поля приходят строкой ("79990.00") */
  price: string
  quantity: number
  /** Обложка — первое из images (локально относительный /media/...), null — фото нет */
  image: string | null
  /** Все фото по порядку, первое — обложка */
  images: ProductPhoto[]
  delivery_methods: DeliveryMethod[]
  status: ProductStatus
  status_display: string
  created_at: string
  updated_at: string
}

/** Поля товара, которые задаёт продавец (кроме фото) */
export interface ProductFieldsPayload {
  title: string
  price: string
  quantity?: number
  description?: string
  /** Хотя бы один способ; самовывоз — только если у магазина указан адрес */
  delivery_method_ids: number[]
}

export interface ProductCreatePayload extends ProductFieldsPayload {
  /** Фото по порядку, первое станет обложкой */
  images?: File[]
}

/** images — новые фото, добавляются в конец; удаление и порядок — отдельными запросами */
export type ProductUpdatePayload = Partial<ProductFieldsPayload> & { images?: File[] }

export interface ProductListParams extends ProductFilterParams {
  page?: number
}

// --- Заказы ---

/** ready — «готов к выдаче» (самовывоз) или «передан курьеру» (курьер маркета) */
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

/** Заказ в кабинете продавца (SellerOrderSerializer) */
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

const shopPath = (shopId: number) => `/seller/shops/${shopId}`

export const sellerApi = {
  profile: (options?: RequestOptions) => apiRequest<SellerProfile>('/seller/profile/', options),

  listShops: (options?: RequestOptions) => apiRequest<Shop[]>('/seller/shops/', options),

  getShop: (shopId: number, options?: RequestOptions) => apiRequest<Shop>(`${shopPath(shopId)}/`, options),

  createShop: (payload: ShopPayload) => apiRequest<Shop>('/seller/shops/', { method: 'POST', json: payload }),

  updateShop: (shopId: number, payload: Partial<ShopPayload>) =>
    apiRequest<Shop>(`${shopPath(shopId)}/`, { method: 'PATCH', json: payload }),

  listProducts: (shopId: number, { page, ...filters }: ProductListParams = {}, options?: RequestOptions) =>
    apiRequest<Paginated<Product>>(
      withQuery(`${shopPath(shopId)}/products/`, { page, ...productFilterQuery(filters) }),
      options,
    ),

  getProduct: (shopId: number, productId: number, options?: RequestOptions) =>
    apiRequest<Product>(`${shopPath(shopId)}/products/${productId}/`, options),

  /** multipart: вместе с полями уходят файлы фото */
  createProduct: (shopId: number, payload: ProductCreatePayload) =>
    apiRequest<Product>(`${shopPath(shopId)}/products/`, { method: 'POST', body: toFormData(payload) }),

  /** Изменить товар. Переданные delivery_method_ids заменяют набор целиком; новые фото — multipart. */
  updateProduct: (shopId: number, productId: number, payload: ProductUpdatePayload) =>
    apiRequest<Product>(
      `${shopPath(shopId)}/products/${productId}/`,
      payload.images?.length
        ? { method: 'PATCH', body: toFormData(payload) }
        : { method: 'PATCH', json: { ...payload, images: undefined } },
    ),

  /** Удалить фото; если это была обложка, ей станет следующее */
  deleteProductPhoto: (shopId: number, productId: number, photoId: number) =>
    apiRequest<null>(`${shopPath(shopId)}/products/${productId}/images/${photoId}/`, { method: 'DELETE' }),

  /** Новый порядок всех фото товара (первое станет обложкой) */
  reorderProductPhotos: (shopId: number, productId: number, ids: number[]) =>
    apiRequest<ProductPhoto[]>(`${shopPath(shopId)}/products/${productId}/images/order/`, {
      method: 'PUT',
      json: { ids },
    }),

  /** Снять с продажи (мягкое удаление на бэке) */
  archiveProduct: (shopId: number, productId: number) =>
    apiRequest<null>(`${shopPath(shopId)}/products/${productId}/`, { method: 'DELETE' }),

  listOrders: (shopId: number, params: OrderListParams = {}, options?: RequestOptions) =>
    apiRequest<Paginated<Order>>(
      withQuery(`${shopPath(shopId)}/orders/`, { page: params.page, status: params.status }),
      options,
    ),

  /** Перевести заказ в статус из available_statuses; ответ — заказ с новыми действиями */
  changeOrderStatus: (shopId: number, orderId: number, status: OrderStatus) =>
    apiRequest<Order>(`${shopPath(shopId)}/orders/${orderId}/status/`, { method: 'POST', json: { status } }),
}
