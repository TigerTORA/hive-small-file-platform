import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

export interface Cluster {
  id?: number
  name: string
  hive_metastore_url: string
  hdfs_namenode_url: string
  small_file_threshold?: number
}

export interface TableMetric {
  id: number
  cluster_id: number
  database_name: string
  table_name: string
  total_files: number
  small_files: number
  total_size: number
  avg_file_size: number
  scan_time: string
}

// Cluster operations
export const getClusters = () => api.get('/clusters')
export const createCluster = (cluster: Cluster) => api.post('/clusters', cluster)
export const deleteCluster = (id: number) => api.delete(`/clusters/${id}`)
export const testCluster = (id: number) => api.post(`/clusters/${id}/test`)

// Database and table discovery
export const getDatabases = (clusterId: number) => api.get(`/clusters/${clusterId}/databases`)
export const getTables = (clusterId: number, database: string) => 
  api.get(`/clusters/${clusterId}/databases/${database}/tables`)

// Scanning operations
export const scanTables = (data: {
  cluster_id: number
  database_name: string
  table_name?: string
}) => api.post('/scan', data)

// Metrics
export const getMetrics = (clusterId: number, database?: string) => {
  const params = database ? { cluster_id: clusterId, database_name: database } : { cluster_id: clusterId }
  return api.get('/metrics', { params })
}

export const getSummary = (clusterId: number) => 
  api.get('/metrics/summary', { params: { cluster_id: clusterId } })

export const getAnalysis = (clusterId: number) => 
  api.get(`/analysis/${clusterId}`)

export default api