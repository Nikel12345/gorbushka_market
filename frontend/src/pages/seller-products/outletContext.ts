import { useOutletContext } from 'react-router'

/** Что список товаров даёт своим вложенным диалогам (карточка, добавление). */
export interface ProductsOutletContext {
  closeDialog: () => void
  onProductCreated: () => void
  /** Товар изменён (например, фото) — обновить список, диалог остаётся открытым */
  onProductUpdated: () => void
  onProductArchived: () => void
}

export function useProductsOutlet() {
  return useOutletContext<ProductsOutletContext>()
}
