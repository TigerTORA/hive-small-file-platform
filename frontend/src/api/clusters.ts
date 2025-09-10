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
  }
}