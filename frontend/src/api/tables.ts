import api from './index'

export interface TableMetric {
  id: number
  cluster_id: number
  database_name: string
  table_name: string
  table_path: string
  
  // Enhanced metadata fields
  table_type?: string
  storage_format?: string
  input_format?: string
  output_format?: string
  serde_lib?: string
  table_owner?: string
  table_create_time?: string
  partition_columns?: string
  
  // File metrics
  total_files: number
  small_files: number
  total_size: number
  avg_file_size: number
  
  // Partition info
  is_partitioned: boolean
  partition_count: number
  
  // Scan metadata
  scan_time: string
  scan_duration: number
}

export interface SmallFileSummary {
  total_tables: number
  total_files: number
  total_small_files: number
  avg_file_size: number
  small_file_ratio: number
}

export const tablesApi = {
  // 获取表的小文件指标 (分页)
  getTableMetrics(params: {
    cluster_id: number
    page?: number
    page_size?: number
    database_name?: string
  }): Promise<{ items: TableMetric[], total: number }> {
    return api.get('/tables/metrics', { params })
  },

  // 获取表的小文件指标 (不分页)
  getMetrics(clusterId: number, databaseName?: string): Promise<TableMetric[]> {
    const params: any = { cluster_id: clusterId }
    if (databaseName) {
      params.database_name = databaseName
    }
    return api.get('/tables/metrics', { params })
  },

  // 获取集群统计信息
  getClusterStats(clusterId: number): Promise<{
    total_databases: number
    total_tables: number
    small_file_tables: number
    total_small_files: number
  }> {
    return api.get(`/clusters/${clusterId}/stats`)
  },

  // 获取数据库列表
  getDatabases(clusterId: number): Promise<string[]> {
    return api.get(`/clusters/${clusterId}/databases`)
  },

  // 获取小文件摘要统计
  getSmallFileSummary(clusterId: number): Promise<SmallFileSummary> {
    return api.get('/tables/small-files', {
      params: { cluster_id: clusterId }
    })
  },

  // 获取小文件分析报告
  getSmallFilesAnalysis(clusterId: number): Promise<{
    total_tables: number
    affected_tables: number
    total_small_files: number
    potential_savings: number
    table_details: any[]
  }> {
    return api.get(`/clusters/${clusterId}/analysis`)
  },

  // 扫描所有数据库
  scanAllDatabases(clusterId: number): Promise<any> {
    return api.post(`/tables/scan/${clusterId}`)
  },

  // 扫描指定数据库
  scanDatabase(clusterId: number, databaseName: string): Promise<any> {
    return api.post(`/tables/scan/${clusterId}/${databaseName}`)
  },

  // 扫描单个表
  scanTable(clusterId: number, databaseName: string, tableName: string): Promise<any> {
    return api.post(`/tables/scan-table/${clusterId}/${databaseName}/${tableName}`)
  },

  // 触发表扫描 (保持兼容性)
  triggerScan(clusterId: number, databaseName?: string, tableName?: string): Promise<any> {
    return api.post('/tables/scan', {
      cluster_id: clusterId,
      database_name: databaseName,
      table_name: tableName
    })
  }
}