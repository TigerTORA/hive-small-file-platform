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
  // 获取表的小文件指标
  getMetrics(clusterId: number, databaseName?: string): Promise<TableMetric[]> {
    const params: any = { cluster_id: clusterId }
    if (databaseName) {
      params.database_name = databaseName
    }
    return api.get('/tables/metrics', { params })
  },

  // 获取小文件摘要统计
  getSmallFileSummary(clusterId: number): Promise<SmallFileSummary> {
    return api.get('/tables/small-files', {
      params: { cluster_id: clusterId }
    })
  },

  // 触发表扫描
  triggerScan(clusterId: number, databaseName?: string, tableName?: string): Promise<any> {
    return api.post('/tables/scan', {
      cluster_id: clusterId,
      database_name: databaseName,
      table_name: tableName
    })
  }
}