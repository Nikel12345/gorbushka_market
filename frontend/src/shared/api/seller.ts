import type { User } from './auth'
import { apiRequest, type ApiRequestInit } from './client'
import { withQuery } from './query'
import type { Paginated } from './types'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

// --- Магазины и профиль ---

export interface ShopBrief {
  id: number
  name: string
}

export interface Shop extends ShopBrief {
  description: string
  created_at: string
  updated_at: string
}

export interface ShopCreatePayload {
  name: string
  description?: string
}

export interface SellerProfile extends User {
  shops: ShopBrief[]
}

// --- Товары ---

export type ProductStatus = 'active' | 'archived'

export interface Product {
  id: number
  title: string
  description: string
  /** Денежные поля приходят строкой ("79990.00") */
  price: string
  quantity: number
  status: ProductStatus
  status_display: string
  created_at: string
  updated_at: string
}

export interface ProductCreatePayload {
  title: string
  price: string
  quantity?: number
  description?: string
}

export interface ProductListParams {
  page?: number
}

// --- Заказы ---

export type OrderStatus = 'new' | 'confirmed' | 'completed' | 'cancelled'

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
  price: string
  quantity: number
  total: string
}

export interface Order {
  id: number
  status: OrderStatus
  status_display: string
  total_amount: string
  buyer: OrderBuyer
  items: OrderItem[]
  created_at: string
  updated_at: string
}

export interface OrderListParams {
  page?: number
  status?: OrderStatus
}

const shopPath = (shopId: number) => `/seller/shops/${shopId}`

export const sellerApi = {
  profile: (options?: RequestOptions) => apiRequest<SellerProfile>('/seller/profile/', options),

  createShop: (payload: ShopCreatePayload) =>
    apiRequest<Shop>('/seller/shops/', { method: 'POST', json: payload }),

  listProducts: (shopId: number, params: ProductListParams = {}, options?: RequestOptions) =>
    apiRequest<Paginated<Product>>(
      withQuery(`${shopPath(shopId)}/products/`, { page: params.page }),
      options,
    ),

  getProduct: (shopId: number, productId: number, options?: RequestOptions) =>
    apiRequest<Product>(`${shopPath(shopId)}/products/${productId}/`, options),

  createProduct: (shopId: number, payload: ProductCreatePayload) =>
    apiRequest<Product>(`${shopPath(shopId)}/products/`, { method: 'POST', json: payload }),

  /** Снять с продажи (мягкое удаление на бэке) */
  archiveProduct: (shopId: number, productId: number) =>
    apiRequest<null>(`${shopPath(shopId)}/products/${productId}/`, { method: 'DELETE' }),

  listOrders: (shopId: number, params: OrderListParams = {}, options?: RequestOptions) =>
    apiRequest<Paginated<Order>>(
      withQuery(`${shopPath(shopId)}/orders/`, { page: params.page, status: params.status }),
      options,
    ),
}
