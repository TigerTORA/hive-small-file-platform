import api from './index'

export interface DashboardSummary {
  total_clusters: number
  active_clusters: number
  total_tables: number
  monitored_tables: number
  total_files: number
  total_small_files: number
  small_file_ratio: number
  total_size_gb: number
  small_file_size_gb: number
}

export interface TrendPoint {
  date: string
  small_files: number
  total_files: number
  ratio: number
}

export interface FileDistributionItem {
  size_range: string
  count: number
  size_gb: number
  percentage: number
}

export interface TopTable {
  cluster_name: string
  database_name: string
  table_name: string
  small_files: number
  total_files: number
  small_file_ratio: number
  total_size_gb: number
  last_scan: string
}

export interface RecentTask {
  id: number
  task_name: string
  cluster_name: string
  table_name: string
  status: string
  created_time: string
  updated_time?: string
  small_files_merged?: number
}

export interface ClusterStats {
  id: number
  name: string
  description: string
  table_count: number
  total_files: number
  small_files: number
  small_file_ratio: number
  total_size_gb: number
  recent_tasks: number
  status: string
}

export interface TableFileCountItem {
  table_id: string // cluster_id:database:table format
  cluster_name: string
  database_name: string
  table_name: string
  current_files: number
  trend_7d: number // percentage change
  trend_30d: number
  last_scan: string
}

export interface TableFileCountPoint {
  date: string
  table_name: string
  database_name: string
  cluster_name: string
  total_files: number
  small_files: number
  ratio: number
}

// API 接口
export const dashboardApi = {
  // 获取仪表盘概要统计
  getSummary(): Promise<DashboardSummary> {
    return api.get('/dashboard/summary')
  },

  // 获取小文件趋势数据
  getTrends(clusterId?: number, days: number = 30): Promise<TrendPoint[]> {
    const params: any = { days }
    if (clusterId) {
      params.cluster_id = clusterId
    }
    return api.get('/dashboard/trends', { params })
  },

  // 获取文件大小分布
  getFileDistribution(clusterId?: number): Promise<FileDistributionItem[]> {
    const params: any = {}
    if (clusterId) {
      params.cluster_id = clusterId
    }
    return api.get('/dashboard/file-distribution', { params })
  },

  // 获取TOP表格（小文件最多的表）
  getTopTables(clusterId?: number, limit: number = 10): Promise<TopTable[]> {
    const params: any = { limit }
    if (clusterId) {
      params.cluster_id = clusterId
    }
    return api.get('/dashboard/top-tables', { params })
  },

  // 获取最近任务
  getRecentTasks(limit: number = 20, status?: string): Promise<RecentTask[]> {
    const params: any = { limit }
    if (status) {
      params.status = status
    }
    return api.get('/dashboard/recent-tasks', { params })
  },

  // 获取集群统计详情
  getClusterStats(): Promise<{
    clusters: ClusterStats[]
    summary: {
      total_clusters: number
      active_clusters: number
    }
  }> {
    return api.get('/dashboard/cluster-stats')
  },

  // 获取表文件数列表（含趋势信息）
  getTableFileCounts(clusterId?: number, limit: number = 20): Promise<TableFileCountItem[]> {
    const params: any = { limit }
    if (clusterId) {
      params.cluster_id = clusterId
    }
    return api.get('/dashboard/table-file-counts', { params })
  },

  // 获取单表文件数趋势
  getTableFileTrends(tableId: string, days: number = 30): Promise<TableFileCountPoint[]> {
    const params = { days }
    return api.get(`/dashboard/table-file-trends/${encodeURIComponent(tableId)}`, { params })
  }
}
