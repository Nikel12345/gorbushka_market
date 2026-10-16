import { apiRequest, type ApiRequestInit } from './client'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

/** Части баланса (BalanceSerializer). Денежные поля — строкой. */
export interface Balance {
  /** Деньги: можно тратить и выводить */
  available: string
  bonus: string
  /** Выручка продавца до выдачи заказов */
  frozen: string
  /** Для покупок: деньги + бонусы */
  spendable: string
}

export const walletApi = {
  balance: (options?: RequestOptions) => apiRequest<Balance>('/me/balance/', options),
}
