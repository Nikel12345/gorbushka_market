import { useOutletContext } from 'react-router'

/** Что список товаров даёт своим вложенным диалогам (карточка, добавление). */
export interface ProductsOutletContext {
  closeDialog: () => void
  onProductCreated: () => void
  onProductArchived: () => void
}

export function useProductsOutlet() {
  return useOutletContext<ProductsOutletContext>()
}
