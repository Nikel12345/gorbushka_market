import { apiRequest } from './client'

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  /** "+79991234567"; пусто — не указан */
  phone: string
  /** Сотрудник магазина: ему доступна админка (/seller) */
  is_staff: boolean
  date_joined: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload extends LoginPayload {
  first_name?: string
  last_name?: string
}

export const authApi = {
  me: () => apiRequest<User>('/auth/me/'),
  login: (payload: LoginPayload) =>
    apiRequest<User>('/auth/login/', { method: 'POST', json: payload }),
  register: (payload: RegisterPayload) =>
    apiRequest<User>('/auth/register/', { method: 'POST', json: payload }),
  logout: () => apiRequest<null>('/auth/logout/', { method: 'POST' }),
}
