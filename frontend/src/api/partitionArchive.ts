/**
 * 分区归档API客户端
 */
import http from './index'

export interface ColdPartition {
  database_name: string
  table_name: string
  partition_name: string
  partition_path: string
  days_since_access: number
  last_access_time: string | null
  partition_size: number
  partition_metric_id: number
}

export interface ColdPartitionsSummary {
  cluster_id: number
  cluster_name: string
  total_partitions: number
  cold_partitions: number
  cold_ratio: number
  threshold_days: number
  distribution: {
    very_cold_6m_plus: number
    cold_3_6m: number
    warm_under_3m: number
  }
  cold_partitions_total_size: number
  sample_cold_partitions: ColdPartition[]
  summary_timestamp: string
  filters: {
    database_name: string | null
    table_name: string | null
  }
}

export interface ArchivedPartition {
  database_name: string
  table_name: string
  partition_name: string
  archive_location: string
  archived_at: string | null
  days_since_access: number
  last_access_time: string | null
  total_size: number
  file_count: number
  archive_status: string
}

export interface PartitionArchiveResult {
  status: string
  partition_full_name: string
  original_location?: string
  archive_location: string
  files_moved?: number
  moved_files?: Array<{
    source: string
    target: string
    size?: number
  }>
  archived_at: string
  cluster_id: number
  cluster_name: string
}

export interface PartitionRestoreResult {
  status: string
  partition_full_name: string
  archive_location?: string
  restored_location: string
  files_restored?: number
  restored_files?: Array<{
    archive: string
    restored: string
    size?: number
  }>
  restored_at: string
  cluster_id: number
  cluster_name: string
}

export interface PartitionArchiveStatistics {
  cluster_id: number
  cluster_name: string
  statistics: {
    total_partitions: number
    archived_partitions: number
    active_partitions: number
    archive_ratio: number
    total_archived_size: number
    archive_root_path: string
  }
  recent_archived_partitions: ArchivedPartition[]
  statistics_timestamp: string
}

export interface ScanColdPartitionsRequest {
  database_name?: string
  table_name?: string
  cold_days_threshold?: number
  min_partition_size?: number
}

export interface ScanColdPartitionsResult {
  total_partitions_scanned: number
  cold_partitions_found: number
  partitions_updated: number
  cold_partitions: ColdPartition[]
  threshold_days: number
  min_partition_size: number
  scan_timestamp: string
  cluster_id: number
  cluster_name: string
}

export interface BatchArchiveRequest {
  partitions: Array<{
    database_name: string
    table_name: string
    partition_name: string
  }>
  force?: boolean
}

export interface BatchArchiveResult {
  total_partitions: number
  successful_archives: number
  failed_archives: number
  archive_results: PartitionArchiveResult[]
  error_details: Array<{
    partition_full_name: string
    error: string
  }>
  batch_timestamp: string
  cluster_id: number
  cluster_name: string
}

/**
 * 扫描冷数据分区
 */
export const scanColdPartitions = (clusterId: number, params: ScanColdPartitionsRequest = {}) => {
  return http.post<ScanColdPartitionsResult>(`/partition-archiving/scan-cold-partitions/${clusterId}`, params)
}

/**
 * 获取冷分区摘要
 */
export const getColdPartitionsSummary = (
  clusterId: number,
  databaseName?: string,
  tableName?: string
) => {
  const params = new URLSearchParams()
  if (databaseName) params.append('database_name', databaseName)
  if (tableName) params.append('table_name', tableName)

  return http.get<ColdPartitionsSummary>(
    `/partition-archiving/cold-partitions-summary/${clusterId}?${params.toString()}`
  )
}

/**
 * 获取冷分区列表
 */
export const getColdPartitionsList = (
  clusterId: number,
  coldnessLevel: 'very_cold' | 'cold' | 'warm' = 'cold',
  databaseName?: string,
  tableName?: string,
  limit: number = 100
) => {
  const params = new URLSearchParams()
  params.append('coldness_level', coldnessLevel)
  params.append('limit', limit.toString())
  if (databaseName) params.append('database_name', databaseName)
  if (tableName) params.append('table_name', tableName)

  return http.get<ColdPartition[]>(
    `/partition-archiving/cold-partitions-list/${clusterId}?${params.toString()}`
  )
}

/**
 * 归档单个分区
 */
export const archivePartition = (
  clusterId: number,
  databaseName: string,
  tableName: string,
  partitionName: string,
  force: boolean = false
) => {
  const params = new URLSearchParams()
  if (force) params.append('force', 'true')

  return http.post<PartitionArchiveResult>(
    `/partition-archiving/archive-partition/${clusterId}/${databaseName}/${tableName}/${partitionName}?${params.toString()}`
  )
}

/**
 * 恢复单个分区
 */
export const restorePartition = (
  clusterId: number,
  databaseName: string,
  tableName: string,
  partitionName: string
) => {
  return http.post<PartitionRestoreResult>(
    `/partition-archiving/restore-partition/${clusterId}/${databaseName}/${tableName}/${partitionName}`
  )
}

/**
 * 批量归档分区
 */
export const batchArchivePartitions = (clusterId: number, request: BatchArchiveRequest) => {
  return http.post<BatchArchiveResult>(`/partition-archiving/batch-archive-partitions/${clusterId}`, request)
}

/**
 * 获取分区归档状态
 */
export const getPartitionArchiveStatus = (
  clusterId: number,
  databaseName: string,
  tableName: string,
  partitionName: string
) => {
  return http.get<{
    partition_full_name: string
    archive_status: string
    archive_location: string | null
    archived_at: string | null
    is_cold_data: boolean
    days_since_last_access: number | null
    last_access_time: string | null
    total_size: number | null
    file_count: number | null
  }>(`/partition-archiving/partition-archive-status/${clusterId}/${databaseName}/${tableName}/${partitionName}`)
}

/**
 * 获取已归档分区列表
 */
export const getArchivedPartitions = (
  clusterId: number,
  databaseName?: string,
  tableName?: string,
  limit: number = 100
) => {
  const params = new URLSearchParams()
  params.append('limit', limit.toString())
  if (databaseName) params.append('database_name', databaseName)
  if (tableName) params.append('table_name', tableName)

  return http.get<{
    cluster_id: number
    cluster_name: string
    total_archived_partitions: number
    total_archived_size: number
    archived_partitions: ArchivedPartition[]
    query_timestamp: string
    filters: {
      database_name: string | null
      table_name: string | null
    }
  }>(`/partition-archiving/archived-partitions/${clusterId}?${params.toString()}`)
}

/**
 * 获取分区归档统计信息
 */
export const getPartitionArchiveStatistics = (clusterId: number, queryRangeDays: number = 30) => {
  const params = new URLSearchParams()
  params.append('query_range_days', queryRangeDays.toString())

  return http.get<{
    cluster_id: number
    statistics: PartitionArchiveStatistics
    query_range_days: number
  }>(`/partition-archiving/partition-archive-statistics/${clusterId}?${params.toString()}`)
}

/**
 * 获取分区冷热分布
 */
export const getPartitionColdnessDistribution = (
  clusterId: number,
  databaseName?: string,
  tableName?: string
) => {
  const params = new URLSearchParams()
  if (databaseName) params.append('database_name', databaseName)
  if (tableName) params.append('table_name', tableName)

  return http.get<{
    cluster_id: number
    cluster_name: string
    distribution: {
      very_cold_6m_plus: number
      cold_3_6m: number
      warm_under_3m: number
    }
    total_partitions: number
    distribution_timestamp: string
    filters: {
      database_name: string | null
      table_name: string | null
    }
  }>(`/partition-archiving/partition-coldness-distribution/${clusterId}?${params.toString()}`)
}

/**
 * 按策略自动归档
 */
export const autoArchiveByPolicy = (
  clusterId: number,
  request: {
    cold_days_threshold?: number
    min_partition_size?: number
    max_partitions_per_batch?: number
    database_name?: string
    table_name?: string
    dry_run?: boolean
  } = {}
) => {
  return http.post<BatchArchiveResult>(`/partition-archiving/auto-archive-by-policy/${clusterId}`, request)
}