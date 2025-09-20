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

  // Cold data fields
  is_cold_data?: boolean
  days_since_last_access?: number
  last_access_time?: string
  archive_status?: string
  archive_location?: string
  archived_at?: string

  // UI state fields
  archiving?: boolean
  restoring?: boolean
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
  }): Promise<{ items: TableMetric[]; total: number }> {
    return api.get('/tables/metrics', { params }).then((data: any) => {
      // Backend usually returns an array of latest TableMetric rows.
      // Normalize to { items, total } and apply client-side paging.
      if (Array.isArray(data)) {
        const total = data.length
        const page = params.page && params.page > 0 ? params.page : 1
        const size = params.page_size && params.page_size > 0 ? params.page_size : total
        const start = (page - 1) * size
        const end = start + size
        return { items: data.slice(start, end), total }
      }

      // If API already returns a shape with items/total, pass through safely
      if (data && Array.isArray(data.items)) {
        const total = typeof data.total === 'number' ? data.total : data.items.length
        return { items: data.items, total }
      }

      // Fallback: unknown shape
      return { items: [], total: 0 }
    })
  },

  // 获取分区指标（分区表）
  getPartitionMetrics(
    clusterId: number,
    databaseName: string,
    tableName: string,
    page = 1,
    pageSize = 50,
    concurrency = 5
  ): Promise<{ items: any[]; total: number; page: number; page_size: number }> {
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
    return api
      .get('/tables/small-files', {
        params: { cluster_id: clusterId }
      })
      .then(response => {
        // 转换数据格式以匹配前端期望的结构
        return {
          total_tables: response.total_tables,
          affected_tables: Math.round((response.total_tables * response.small_file_ratio) / 100),
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
  scanTable(
    clusterId: number,
    databaseName: string,
    tableName: string,
    strictReal: boolean = true
  ): Promise<any> {
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
  },

  // 冷数据扫描
  scanColdData(clusterId: number, coldDaysThreshold = 90, databaseName?: string): Promise<any> {
    const params: any = { cold_days_threshold: coldDaysThreshold }
    if (databaseName) {
      params.database_name = databaseName
    }
    return api.post(`/tables/scan-cold-data/${clusterId}`, null, { params })
  },

  // 获取冷数据摘要
  getColdDataSummary(clusterId: number): Promise<any> {
    return api.get(`/tables/cold-data-summary/${clusterId}`)
  },

  // 获取冷数据表列表
  getColdDataList(clusterId: number, page = 1, pageSize = 20): Promise<any> {
    return api.get(`/tables/cold-data-list/${clusterId}`, {
      params: { page, page_size: pageSize }
    })
  },

  // 归档表
  archiveTable(
    clusterId: number,
    databaseName: string,
    tableName: string,
    force = false
  ): Promise<any> {
    const params: any = { force }
    return api.post(`/tables/archive-table/${clusterId}/${databaseName}/${tableName}`, null, {
      params
    })
  },

  // 归档表（带后台任务与进度）
  archiveTableWithProgress(
    clusterId: number,
    databaseName: string,
    tableName: string,
    force = false
  ): Promise<{ task_id: string }> {
    const params: any = { force }
    return api.post(`/table-archiving/archive-with-progress/${clusterId}/${databaseName}/${tableName}`, null, { params })
  },

  // 恢复表
  restoreTable(clusterId: number, databaseName: string, tableName: string): Promise<any> {
    return api.post(`/tables/restore-table/${clusterId}/${databaseName}/${tableName}`)
  },

  // 获取表归档状态
  getArchiveStatus(clusterId: number, databaseName: string, tableName: string): Promise<any> {
    return api.get(`/tables/archive-status/${clusterId}/${databaseName}/${tableName}`)
  },

  // 获取已归档表列表
  getArchivedTables(clusterId: number, limit = 100): Promise<any> {
    return api.get(`/tables/archived-tables/${clusterId}`, {
      params: { limit }
    })
  },

  // 获取归档统计信息
  getArchiveStatistics(clusterId: number): Promise<any> {
    return api.get(`/tables/archive-statistics/${clusterId}`)
  }
}
