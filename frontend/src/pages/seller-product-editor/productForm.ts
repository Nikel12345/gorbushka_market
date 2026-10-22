// Логика формы товара (добавление и правка): значения полей, проверка, payload для API
import { categoryPathLabel, isAvailableIn } from '@/features/seller'
import {
  deliveryApi,
  type Category,
  type Characteristic,
  type CharacteristicBrief,
  type DeliveryMethod,
  type FieldErrors,
  type Product,
  type ProductFieldsPayload,
  type ProductGroup,
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

/** Характеристика товара в форме. valueId null — строку добавили, значение ещё не выбрали */
export interface CharacteristicRow {
  characteristicId: number
  valueId: number | null
}

/** Поля товара в том виде, как их вводят (строки) */
export interface ProductFormValues {
  title: string
  /** В долларах */
  priceUsd: string
  quantity: string
  description: string
  deliveryIds: number[]
  categoryId: number | null
  groupId: number | null
  characteristics: CharacteristicRow[]
}

export const EMPTY_PRODUCT_FORM: ProductFormValues = {
  title: '',
  priceUsd: '',
  quantity: '1',
  description: '',
  deliveryIds: [],
  categoryId: null,
  groupId: null,
  characteristics: [],
}

/** "999.00" → "999", "1299.90" → "1299,90": как ввёл бы человек */
function priceForInput(price: string): string {
  return price.replace(/\.00$/, '').replace('.', ',')
}

export function productToFormValues(product: Product): ProductFormValues {
  return {
    title: product.title,
    priceUsd: priceForInput(product.price_usd),
    quantity: String(product.quantity),
    description: product.description,
    deliveryIds: product.delivery_methods.map((method) => method.id),
    categoryId: product.category?.id ?? null,
    groupId: product.group?.id ?? null,
    characteristics: product.characteristics.map((item) => ({
      characteristicId: item.characteristic_id,
      valueId: item.value_id,
    })),
  }
}

/** "1 299,90" → "1299.90": бэкенд ждёт десятичное число через точку */
function normalizeDecimal(value: string): string {
  return value.replace(/\s/g, '').replace(',', '.')
}

export function toProductPayload(values: ProductFormValues): ProductFieldsPayload {
  const payload: ProductFieldsPayload = {
    title: values.title.trim(),
    price_usd: normalizeDecimal(values.priceUsd),
    description: values.description.trim(),
    delivery_method_ids: values.deliveryIds,
    category_id: values.categoryId,
    group_id: values.groupId,
    // Строки без значения не сохраняем
    characteristic_value_ids: values.characteristics.flatMap((row) => (row.valueId === null ? [] : [row.valueId])),
  }
  // Пусто: при создании сервер поставит 1, при правке останется как было
  if (values.quantity.trim() !== '') payload.quantity = Number(values.quantity)
  return payload
}

/**
 * Строки характеристик для показа: сначала оси группы — у товара в группе они обязательны
 * и убрать их нельзя (если значения ещё нет, строка пустая), потом остальные по порядку добавления.
 */
export function characteristicRows(
  rows: CharacteristicRow[],
  axes: CharacteristicBrief[],
): { row: CharacteristicRow; axis: boolean }[] {
  const axisIds = new Set(axes.map((axis) => axis.id))
  return [
    ...axes.map((axis) => ({
      row: rows.find((row) => row.characteristicId === axis.id) ?? { characteristicId: axis.id, valueId: null },
      axis: true,
    })),
    ...rows.filter((row) => !axisIds.has(row.characteristicId)).map((row) => ({ row, axis: false })),
  ]
}

/** Группа не подходит категории товара: её товары лежат в другой ветке. Подходит — undefined */
export function groupCategoryProblem(
  group: ProductGroup | null | undefined,
  categoryId: number | null,
  categories: Category[] | undefined,
): string | undefined {
  if (!group?.category || !categories || isAvailableIn(categories, group.category, categoryId)) return undefined
  return `Группа «${group.name}» — для товаров категории «${categoryPathLabel(categories, group.category)}» и её подкатегорий. Выберите такую категорию или другую группу.`
}

/** Характеристики товара, недоступные в выбранной категории (их перенесли или сменили категорию товара) */
export function unavailableCharacteristics(
  rows: CharacteristicRow[],
  characteristics: Characteristic[] | undefined,
  categoryId: number | null,
  categories: Category[] | undefined,
): Characteristic[] {
  if (!characteristics || !categories) return []
  const ids = new Set(rows.map((row) => row.characteristicId))
  return characteristics.filter(
    (item) => ids.has(item.id) && !isAvailableIn(categories, item.category, categoryId),
  )
}

interface ValidationContext {
  shop: Shop
  methods: DeliveryMethodsRequest
  /** Выбранная группа (с осями) */
  group: ProductGroup | null | undefined
  characteristics: Characteristic[] | undefined
  categories: Category[] | undefined
}

/** Проверки до отправки — то, что сервер не проверяет или проверяет без подсказки, что делать. */
export function validateProductForm(
  values: ProductFormValues,
  { shop, methods, group, characteristics, categories }: ValidationContext,
): FieldErrors {
  const errors: FieldErrors = {}
  const axes = group?.axes ?? []

  if (values.deliveryIds.length === 0) {
    errors.delivery_method_ids = ['Выберите хотя бы один способ получения.']
  } else if (
    methods.data?.some((method) => values.deliveryIds.includes(method.id) && needsShopAddress(method, shop))
  ) {
    errors.delivery_method_ids = ['Самовывоз недоступен, пока у магазина не указан адрес.']
  }

  const missing = axes.filter(
    (axis) => !values.characteristics.some((row) => row.characteristicId === axis.id && row.valueId !== null),
  )
  const characteristicErrors: string[] = []
  if (missing.length > 0) {
    const names = missing.map((axis) => axis.name).join(', ')
    characteristicErrors.push(`Выберите: ${names} — по ним различаются товары группы.`)
  }
  const unavailable = unavailableCharacteristics(values.characteristics, characteristics, values.categoryId, categories)
  if (unavailable.length > 0) {
    const names = unavailable.map((item) => `«${item.name}»`).join(', ')
    characteristicErrors.push(`Недоступны в категории товара: ${names}. Уберите их или выберите другую категорию.`)
  }
  if (characteristicErrors.length > 0) errors.characteristics = characteristicErrors

  const groupProblem = groupCategoryProblem(group, values.categoryId, categories)
  if (groupProblem) errors.group = [groupProblem]

  return errors
}

const VARIANT_FIELDS = ['group_id', 'characteristic_value_ids']

/**
 * Ошибки сервера → поля формы. Нарушения правил вариантов («такой вариант уже есть»,
 * «не указана ось») приходят общим detail с code — показываем их у блока вариантов, а не сверху;
 * «товар вне категории группы» — у выбора группы.
 */
export function placeServerErrors(errors: FieldErrors): FieldErrors {
  const placed: FieldErrors = {}
  const variantErrors: string[] = []
  const code = errors.code?.[0] ?? ''
  const outsideGroup = code === 'variant_product_outside_category'
  const isVariantRule = code.startsWith('variant_') || code.startsWith('characteristic_')

  for (const [field, messages] of Object.entries(errors)) {
    if (field === 'code') continue
    if (outsideGroup && field === 'non_field_errors') {
      placed.group = messages
    } else if (VARIANT_FIELDS.includes(field) || (isVariantRule && field === 'non_field_errors')) {
      variantErrors.push(...messages)
    } else {
      placed[field] = messages
    }
  }
  if (variantErrors.length > 0) placed.characteristics = variantErrors
  return placed
}
