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
  files_reduced: number
  size_saved_gb: number
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
  files_before?: number | null
  files_after?: number | null
  files_reduced?: number | null
  size_saved?: number | null
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
// New interfaces for enhanced dashboard
export interface FileClassificationItem {
  category: string
  count: number
  size_gb: number
  percentage: number
  description: string
}

export interface ColdDataItem {
  cluster_name: string
  database_name: string
  table_name: string
  partition_name?: string
  last_access_time?: string
  days_since_last_access?: number
  total_size_gb: number
  file_count: number
}

export interface StorageFormatItem {
  format_name: string
  table_count: number
  total_size_gb: number
  small_files: number
  total_files: number
  percentage: number
}

export interface CompressionFormatItem {
  compression_name: string
  table_count: number
  total_size_gb: number
  small_files: number
  total_files: number
  percentage: number
}

export interface FormatCompressionItem {
  format_combination: string
  storage_format: string
  compression_format: string
  table_count: number
  total_size_gb: number
  small_files: number
  total_files: number
  percentage: number
}

export interface DetailedColdnessStats {
  partitions: { count: number; size_gb: number }
  tables: { count: number; size_gb: number }
  total_size_gb: number
}

export interface EnhancedColdnessDistribution {
  cluster_id: number
  cluster_name: string
  distribution: {
    within_1_day: DetailedColdnessStats
    day_1_to_7: DetailedColdnessStats
    week_1_to_month: DetailedColdnessStats
    month_1_to_3: DetailedColdnessStats
    month_3_to_6: DetailedColdnessStats
    month_6_to_12: DetailedColdnessStats
    year_1_to_3: DetailedColdnessStats
    over_3_years: DetailedColdnessStats
  }
  summary: {
    total_partitions: number
    total_tables: number
    total_size_gb: number
    partition_total_size_gb?: number
  }
  distribution_timestamp: string
}

export const dashboardApi = {
  // 获取仪表盘概要统计
  getSummary(clusterId?: number): Promise<DashboardSummary> {
    const params: Record<string, number> = {}
    if (clusterId) {
      params.cluster_id = clusterId
    }
    return api.get('/dashboard/summary', { params })
  },

  // 获取文件分类统计
  getFileClassification(clusterId?: number): Promise<FileClassificationItem[]> {
    const params: any = {}
    if (clusterId) {
      params.cluster_id = clusterId
    }
    return api.get('/dashboard/file-classification', { params })
  },

  // 获取增强的冷数据分布
  getEnhancedColdnessDistribution(clusterId?: number): Promise<EnhancedColdnessDistribution> {
    const params: any = {}
    if (clusterId) {
      params.cluster_id = clusterId
    }
    return api.get('/dashboard/enhanced-coldness-distribution', { params })
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
  },

  // 获取冷数据排行榜
  getColdestData(limit: number = 10): Promise<ColdDataItem[]> {
    const params = { limit }
    return api.get('/dashboard/coldest-data', { params })
  },

  // 获取存储格式分布统计
  getStorageFormatDistribution(clusterId?: number): Promise<StorageFormatItem[]> {
    const params: any = {}
    if (clusterId) {
      params.cluster_id = clusterId
    }
    return api.get('/dashboard/storage-format-distribution', { params })
  },

  // 获取压缩格式分布统计
  getCompressionFormatDistribution(clusterId?: number): Promise<CompressionFormatItem[]> {
    const params: any = {}
    if (clusterId) {
      params.cluster_id = clusterId
    }
    return api.get('/dashboard/compression-format-distribution', { params })
  },

  // 获取存储格式和压缩格式组合分布统计
  getFormatCompressionDistribution(clusterId?: number): Promise<FormatCompressionItem[]> {
    const params: any = {}
    if (clusterId) {
      params.cluster_id = clusterId
    }
    return api.get('/dashboard/format-compression-distribution', { params })
  }
}
