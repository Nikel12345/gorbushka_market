// Логика формы товара (добавление и правка): значения полей, проверка, payload для API
import {
  deliveryApi,
  type DeliveryMethod,
  type FieldErrors,
  type Product,
  type ProductFieldsPayload,
  type Shop,
} from '@/shared/api'
import { useRequest } from '@/shared/lib'

const loadMethods = (signal: AbortSignal) => deliveryApi.methods({ signal })

/** Справочник способов доставки. Грузит форма товара: он нужен и полю, и проверке перед отправкой. */
export function useDeliveryMethods() {
  return useRequest(loadMethods)
}

export type DeliveryMethodsRequest = ReturnType<typeof useDeliveryMethods>

/** Самовывоз без адреса магазина не выбрать: покупателю некуда будет прийти */
export function needsShopAddress(method: DeliveryMethod, shop: Shop): boolean {
  return method.kind === 'pickup' && !shop.address
}

/** Поля товара в том виде, как их вводят (строки) */
export interface ProductFormValues {
  title: string
  price: string
  quantity: string
  description: string
  deliveryIds: number[]
}

export const EMPTY_PRODUCT_FORM: ProductFormValues = {
  title: '',
  price: '',
  quantity: '1',
  description: '',
  deliveryIds: [],
}

/** "79990.00" → "79990", "1299.90" → "1299,90": как ввёл бы человек */
function priceForInput(price: string): string {
  return price.replace(/\.00$/, '').replace('.', ',')
}

export function productToFormValues(product: Product): ProductFormValues {
  return {
    title: product.title,
    price: priceForInput(product.price),
    quantity: String(product.quantity),
    description: product.description,
    deliveryIds: product.delivery_methods.map((method) => method.id),
  }
}

/** "1 299,90" → "1299.90": бэкенд ждёт десятичное число через точку */
function normalizeDecimal(value: string): string {
  return value.replace(/\s/g, '').replace(',', '.')
}

export function toProductPayload(values: ProductFormValues): ProductFieldsPayload {
  const payload: ProductFieldsPayload = {
    title: values.title.trim(),
    price: normalizeDecimal(values.price),
    description: values.description.trim(),
    delivery_method_ids: values.deliveryIds,
  }
  // Пусто: при создании сервер поставит 1, при правке останется как было
  if (values.quantity.trim() !== '') payload.quantity = Number(values.quantity)
  return payload
}

/** Проверки до отправки — то, что сервер не проверяет или проверяет без подсказки, что делать. */
export function validateProductForm(values: ProductFormValues, shop: Shop, methods: DeliveryMethodsRequest): FieldErrors {
  if (values.deliveryIds.length === 0) {
    return { delivery_method_ids: ['Выберите хотя бы один способ получения.'] }
  }
  const pickupWithoutAddress = methods.data?.some(
    (method) => values.deliveryIds.includes(method.id) && needsShopAddress(method, shop),
  )
  if (pickupWithoutAddress) {
    return { delivery_method_ids: ['Самовывоз недоступен, пока у магазина не указан адрес.'] }
  }
  return {}
}
