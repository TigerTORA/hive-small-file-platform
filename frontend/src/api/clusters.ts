import api from './index'

export interface Cluster {
  id: number
  name: string
  description?: string
  hive_host: string
  hive_port: number
  hive_database: string
  hive_metastore_url: string
  hdfs_namenode_url: string
  hdfs_user: string
  auth_type: string
  hive_username?: string
  hive_password?: string
  yarn_resource_manager_url?: string
  small_file_threshold: number
  scan_enabled: boolean
  status: string
  created_time: string
  updated_time: string
}

export interface ClusterCreate {
  name: string
  description?: string
  hive_host: string
  hive_port?: number
  hive_database?: string
  hive_metastore_url: string
  hdfs_namenode_url: string
  hdfs_user?: string
  auth_type?: string
  hive_username?: string
  hive_password?: string
  yarn_resource_manager_url?: string
  small_file_threshold?: number
  scan_enabled?: boolean
}

export const clustersApi = {
  // 获取集群列表
  list(): Promise<Cluster[]> {
    return api.get('/clusters/')
  },

  // 创建集群
  create(cluster: ClusterCreate): Promise<Cluster> {
    return api.post('/clusters/', cluster)
  },

  // 获取集群详情
  get(id: number): Promise<Cluster> {
    return api.get(`/clusters/${id}`)
  },

  // 更新集群
  update(id: number, cluster: Partial<ClusterCreate>): Promise<Cluster> {
    return api.put(`/clusters/${id}`, cluster)
  },

  // 删除集群
  delete(id: number): Promise<void> {
    return api.delete(`/clusters/${id}`)
  },

  // 测试集群连接
  testConnection(id: number, mode: string = 'mock'): Promise<any> {
    return api.post(`/clusters/${id}/test?mode=${mode}`)
  },

  // 测试真实连接
  testConnectionReal(id: number): Promise<any> {
    return api.post(`/clusters/${id}/test-real`)
  },

  // 创建集群时验证连接
  createWithValidation(cluster: ClusterCreate): Promise<Cluster> {
    return api.post('/clusters/?validate_connection=true', cluster)
  },

  // 测试连接配置（不创建集群）
  testConnectionConfig(cluster: ClusterCreate): Promise<any> {
    return api.post('/clusters/test-connection', cluster)
  },

  // 获取集群统计数据
  getStats(id: number): Promise<{
    total_databases: number
    total_tables: number
    small_file_tables: number
    total_small_files: number
  }> {
    return api.get(`/clusters/${id}/stats`)
  },

  // 增强连接测试
  testConnectionEnhanced(
    id: number,
    options?: {
      connectionTypes?: string[]
      forceRefresh?: boolean
    }
  ): Promise<{
    cluster_id: number
    cluster_name: string
    test_mode: string
    overall_status: string
    total_test_time_ms: number
    tests: Record<
      string,
      {
        status: string
        response_time_ms: number
        failure_type?: string
        error_message?: string
        attempt_count: number
        retry_count: number
      }
    >
    logs: Array<{ level: string; message: string }>
    suggestions: string[]
  }> {
    const params = new URLSearchParams()
    if (options?.forceRefresh) {
      params.append('force_refresh', 'true')
    }
    if (options?.connectionTypes) {
      options.connectionTypes.forEach(type => params.append('connection_types', type))
    }

    const url = `/clusters/${id}/test-enhanced${params.toString() ? `?${params.toString()}` : ''}`
    return api.post(url)
  },

  // 获取连接统计
  getConnectionStatistics(
    id: number,
    hours: number = 24
  ): Promise<{
    cluster_id: number
    cluster_name: string
    total_tests: number
    successful_tests: number
    success_rate: number
    average_response_time_ms: number
    failure_types: Record<string, number>
    period_hours: number
  }> {
    return api.get(`/clusters/${id}/connection-statistics?hours=${hours}`)
  },

  // 获取连接历史
  getConnectionHistory(
    id: number,
    limit: number = 50
  ): Promise<{
    cluster_id: number
    cluster_name: string
    total_records: number
    history: Array<{
      connection_type: string
      status: string
      response_time_ms: number
      failure_type?: string
      error_message?: string
      attempt_count: number
      retry_count: number
      timestamp: string
    }>
  }> {
    return api.get(`/clusters/${id}/connection-history?limit=${limit}`)
  },

  // 获取集群状态
  getStatus(id: number): Promise<{
    cluster_id: number
    cluster_name: string
    status: string
    health_status: string
    last_health_check?: string
    connections: Record<
      string,
      {
        status: string
        last_check?: string
        cached: boolean
      }
    >
  }> {
    return api.get(`/clusters/${id}/status`)
  },

  // 清除连接缓存
  clearConnectionCache(id: number): Promise<{
    cluster_id: number
    cluster_name: string
    message: string
  }> {
    return api.delete(`/clusters/${id}/cache`)
  }
}

// Composition API风格的hook
export const useClustersApi = () => {
  return {
    list: clustersApi.list.bind(clustersApi),
    get: clustersApi.get.bind(clustersApi),
    create: clustersApi.create.bind(clustersApi),
    update: clustersApi.update.bind(clustersApi),
    delete: clustersApi.delete.bind(clustersApi),
    testConnection: clustersApi.testConnection.bind(clustersApi),
    testConnectionReal: clustersApi.testConnectionReal.bind(clustersApi),
    createWithValidation: clustersApi.createWithValidation.bind(clustersApi),
    testConnectionConfig: clustersApi.testConnectionConfig.bind(clustersApi),
    getStats: clustersApi.getStats.bind(clustersApi),
    testConnectionEnhanced: clustersApi.testConnectionEnhanced.bind(clustersApi),
    getConnectionStatistics: clustersApi.getConnectionStatistics.bind(clustersApi),
    getConnectionHistory: clustersApi.getConnectionHistory.bind(clustersApi),
    getStatus: clustersApi.getStatus.bind(clustersApi),
    clearConnectionCache: clustersApi.clearConnectionCache.bind(clustersApi)
  }
}

export default clustersApi
