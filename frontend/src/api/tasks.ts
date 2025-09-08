import api from './index'

export interface MergeTask {
  id: number
  cluster_id: number
  task_name: string
  table_name: string
  database_name: string
  partition_filter?: string
  merge_strategy: 'concatenate' | 'insert_overwrite'
  target_file_size?: number
  status: string
  celery_task_id?: string
  error_message?: string
  files_before?: number
  files_after?: number
  size_saved?: number
  created_time: string
  started_time?: string
  completed_time?: string
}

export interface MergeTaskCreate {
  cluster_id: number
  task_name: string
  table_name: string
  database_name: string
  partition_filter?: string
  merge_strategy?: 'concatenate' | 'insert_overwrite'
  target_file_size?: number
}

export const tasksApi = {
  // 获取任务列表
  list(): Promise<MergeTask[]> {
    return api.get('/tasks/')
  },

  // 创建合并任务
  create(task: MergeTaskCreate): Promise<MergeTask> {
    return api.post('/tasks/', task)
  },

  // 获取任务详情
  get(id: number): Promise<MergeTask> {
    return api.get(`/tasks/${id}`)
  },

  // 执行任务
  execute(id: number): Promise<any> {
    return api.post(`/tasks/${id}/execute`)
  },

  // 取消任务
  cancel(id: number): Promise<any> {
    return api.post(`/tasks/${id}/cancel`)
  },

  // 获取任务日志
  getLogs(id: number): Promise<any[]> {
    return api.get(`/tasks/${id}/logs`)
  }
}