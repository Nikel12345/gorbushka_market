import { apiRequest } from './client'

export interface HealthResponse {
  status: 'ok'
}

export function fetchHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/health/')
}
