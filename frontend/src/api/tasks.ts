import api from './index'

export interface MergeTask {
  id: number
  cluster_id: number
  task_name: string
  table_name: string
  database_name: string
  partition_filter?: string
  merge_strategy: 'concatenate' | 'insert_overwrite' | 'safe_merge'
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
  
  // 执行进度相关字段
  execution_phase?: string  // 当前执行阶段
  progress_percentage?: number  // 执行进度百分比
  estimated_remaining_time?: number  // 预计剩余时间（秒）
  processed_files_count?: number  // 已处理文件数
  total_files_count?: number  // 总文件数
  yarn_application_id?: string  // YARN任务ID
  current_operation?: string  // 当前操作描述
}

export interface MergeTaskCreate {
  cluster_id: number
  task_name: string
  table_name: string
  database_name: string
  partition_filter?: string
  merge_strategy?: 'concatenate' | 'insert_overwrite' | 'safe_merge'
  target_file_size?: number
}

export const tasksApi = {
  // 获取任务列表
  list(): Promise<MergeTask[]> {
    return api.get('/tasks/')
  },

  // 获取集群任务列表
  getByCluster(clusterId: number): Promise<MergeTask[]> {
    return api.get(`/tasks/`, { params: { cluster_id: clusterId } })
  },

  // 创建合并任务
  create(task: MergeTaskCreate): Promise<MergeTask> {
    return api.post('/tasks/', task)
  },

  // 智能创建合并任务（自动策略选择）
  createSmart(params: {
    cluster_id: number
    database_name: string
    table_name: string
    partition_filter?: string
  }): Promise<{
    task: MergeTask
    strategy_info: {
      recommended_strategy: string
      strategy_reason: string
      validation: any
    }
  }> {
    return api.post('/tasks/smart-create', params)
  },

  // 重试任务
  retry(id: number): Promise<any> {
    return api.post(`/tasks/${id}/retry`)
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
  },

  // 获取表信息（包括分区状态）
  getTableInfo(clusterId: number, databaseName: string, tableName: string): Promise<any> {
    return api.get(`/tables/${clusterId}/${databaseName}/${tableName}/info`)
  },

  // 获取表分区列表
  getTablePartitions(clusterId: number, databaseName: string, tableName: string): Promise<any> {
    return api.get(`/tables/${clusterId}/${databaseName}/${tableName}/partitions`)
  },

  // 获取合并预览
  getMergePreview(clusterId: number, databaseName: string, tableName: string, partitionFilter?: string): Promise<any> {
    const params = partitionFilter ? `?partition_filter=${encodeURIComponent(partitionFilter)}` : ''
    return api.post(`/tables/${clusterId}/${databaseName}/${tableName}/merge-preview${params}`)
  },

  // 批量扫描所有数据库
  scanAllDatabases(clusterId: number, maxTablesPerDb: number = 20): Promise<any> {
    return api.post(`/tables/scan-all-databases/${clusterId}?max_tables_per_db=${maxTablesPerDb}`)
  },

  // 获取扫描任务列表（替代废弃的scan-progress API）
  getScanTasks(clusterId?: number): Promise<any> {
    const params = clusterId ? { cluster_id: clusterId } : {}
    return api.get('/scan-tasks/', { params })
  },

  // 获取任务预览
  getTaskPreview(id: number): Promise<any> {
    return api.get(`/tasks/${id}/preview`)
  }
}
