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

  // 获取分区指标（分区表）
  getPartitionMetrics(
    clusterId: number,
    databaseName: string,
    tableName: string,
    page = 1,
    pageSize = 50,
    concurrency = 5
  ): Promise<{ items: any[], total: number, page: number, page_size: number }>{
    return api.get('/tables/partition-metrics', {
      params: { 
        cluster_id: clusterId, 
        database_name: databaseName, 
        table_name: tableName, 
        page, 
        page_size: pageSize,
        concurrency
      }
    })
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
    // 使用实际可用的API端点
    return api.get('/tables/small-files', {
      params: { cluster_id: clusterId }
    }).then(response => {
      // 转换数据格式以匹配前端期望的结构
      return {
        total_tables: response.total_tables,
        affected_tables: Math.round(response.total_tables * response.small_file_ratio / 100),
        total_small_files: response.total_small_files,
        potential_savings: Math.round(response.total_small_files * 128 * 1024), // 假设每个小文件平均节省128KB
        table_details: [] // 暂时返回空数组，等后端提供详细接口
      }
    })
  },

  // 扫描所有数据库（带严格实连与每库表数上限）
  scanAllDatabases(
    clusterId: number,
    strictReal: boolean = true,
    maxTablesPerDb?: number | null
  ): Promise<any> {
    const params: any = { strict_real: strictReal }
    if (typeof maxTablesPerDb === 'number' && maxTablesPerDb > 0) {
      params.max_tables_per_db = maxTablesPerDb
    }
    return api.post(`/tables/scan/${clusterId}` as string, null, { params })
  },

  // 扫描指定数据库（注意：该路径为 Mock 模式；如需严格实连请走 scan-real）
  scanDatabase(clusterId: number, databaseName: string, strictReal: boolean = true): Promise<any> {
    // 后端此端点为 Mock 路径，不读取 strict_real；保留参数以便将来兼容
    return api.post(`/tables/scan/${clusterId}/${databaseName}`)
  },

  // 扫描单个表
  scanTable(clusterId: number, databaseName: string, tableName: string, strictReal: boolean = true): Promise<any> {
    // 当前端点不接受 strict_real 参数；如需严格模式，建议使用统一入口 triggerScan
    return api.post(`/tables/scan-table/${clusterId}/${databaseName}/${tableName}`)
  },

  // 触发表扫描 (保持兼容性) - 支持 strict_real 参数
  triggerScan(
    clusterId: number,
    databaseName?: string,
    tableName?: string,
    strictReal: boolean = true
  ): Promise<any> {
    const data = {
      cluster_id: clusterId,
      database_name: databaseName,
      table_name: tableName
    }
    return api.post('/tables/scan', data, { params: { strict_real: strictReal } })
  }
}
