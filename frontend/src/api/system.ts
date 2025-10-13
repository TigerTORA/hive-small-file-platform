import api from './index'

export interface HealthResponse {
  status: string
  server_config?: {
    host: string
    port: number
    environment?: string
  }
}

export const systemApi = {
  getHealth(): Promise<HealthResponse> {
    return api.get('/health')
  }
}
