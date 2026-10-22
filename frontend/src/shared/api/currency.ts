import { apiRequest, type ApiRequestInit } from './client'

type RequestOptions = Pick<ApiRequestInit, 'signal'>

/** Курс доллара (GET /currency/usd/): по нему цены товаров переводятся из долларов в рубли */
export interface UsdRate {
  /** Рублей за доллар, строкой ("82.8879") */
  rate: string
  /** Дата курса ЦБ (YYYY-MM-DD); null — магазин задал свой постоянный курс */
  date: string | null
}

export const currencyApi = {
  usd: (options?: RequestOptions) => apiRequest<UsdRate>('/currency/usd/', options),
}
