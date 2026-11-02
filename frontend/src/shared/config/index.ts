export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  /**
   * Панель выбора варианта дизайна под поиском. Пока заказчик выбирает — включена;
   * VITE_DESIGN_SWITCHER=off в .env скрывает её, и у всех остаётся вариант по умолчанию.
   */
  designSwitcher: import.meta.env.VITE_DESIGN_SWITCHER !== 'off',
} as const

export { store } from './store'
