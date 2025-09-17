import api from './index'

export interface ScanTask {
  id: number
  task_id: string
  cluster_id: number
  task_type: string
  task_name: string
  status: string
  total_items: number
  completed_items: number
  current_item?: string
  progress_percentage: number
  estimated_remaining_seconds: number
  total_tables_scanned: number
  total_files_found: number
  total_small_files: number
  start_time: string
  end_time?: string
  duration?: number
  error_message?: string
}

export const scanTasksApi = {
  list(clusterId?: number, status?: string, limit: number = 50): Promise<ScanTask[]> {
    const params: any = { limit }
    if (clusterId) params.cluster_id = clusterId
    if (status) params.status = status
    return api.get('/scan-tasks/', { params })
  },

  get(taskId: string): Promise<ScanTask> {
    return api.get(`/scan-tasks/${taskId}`)
  },

  getLogs(taskId: string): Promise<any[]> {
    return api.get(`/scan-tasks/${taskId}/logs`)
  },

  cancel(taskId: string): Promise<any> {
    return api.post(`/scan-tasks/${taskId}/cancel`)
  }
}
