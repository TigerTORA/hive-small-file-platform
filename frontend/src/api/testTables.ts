/**
 * 测试表生成API客户端
 */
import api from './index'

export interface TestTableConfig {
  table_name: string
  database_name: string
  hdfs_base_path: string
  partition_count: number
  files_per_partition: number
  file_size_kb: number
  scenario: 'light' | 'default' | 'heavy' | 'extreme' | 'custom'
  data_generation_mode: 'webhdfs' | 'beeline'
}

export interface TestTableCreateRequest {
  cluster_id: number
  config: TestTableConfig
  force_recreate?: boolean
}

export interface TestTableTask {
  id: string
  cluster_id: number
  config: TestTableConfig
  status: 'pending' | 'running' | 'success' | 'failed'
  progress_percentage: number
  current_phase: string
  current_operation: string
  error_message?: string
  created_time: string
  started_time?: string
  completed_time?: string
  hdfs_files_created?: number
  hive_partitions_added?: number
  total_size_mb?: number
}

export interface TestTableDeleteRequest {
  cluster_id: number
  database_name: string
  table_name: string
  delete_hdfs_data?: boolean
}

export interface TestTableVerifyRequest {
  cluster_id: number
  database_name: string
  table_name: string
}

export interface TestTableVerifyResult {
  table_exists: boolean
  partitions_count: number
  hdfs_files_count: number
  total_size_mb: number
  data_rows_count?: number
  verification_passed: boolean
  issues: string[]
}

export interface ScenarioConfig {
  name: string
  description: string
  config: TestTableConfig
  estimated_files: number
  estimated_size_mb: number
  estimated_duration_minutes: number
}

export interface ValidationConfig {
  table_name: string
  database_name: string
  hdfs_base_path: string
  partition_count: number
  files_per_partition: number
  file_size_kb: number
}

export interface ValidationResult {
  valid: boolean
  error?: string
  config?: TestTableConfig
  estimated_files?: number
  estimated_size_mb?: number
  estimated_duration_minutes?: number
  warnings?: string[]
}

class TestTableApi {
  private baseUrl = '/test-tables'

  /**
   * 获取预设测试场景
   */
  async getScenarios(): Promise<{
    scenarios: Record<string, ScenarioConfig>
    recommendations: Record<string, string>
  }> {
    return api.get(`${this.baseUrl}/scenarios`)
  }

  /**
   * 创建测试表
   */
  async createTestTable(data: TestTableCreateRequest): Promise<TestTableTask> {
    return api.post(`${this.baseUrl}/create`, data)
  }

  /**
   * 获取测试表任务列表
   */
  async listTasks(): Promise<TestTableTask[]> {
    return api.get(`${this.baseUrl}/tasks`)
  }

  /**
   * 获取指定任务详情
   */
  async getTask(taskId: string): Promise<TestTableTask> {
    return api.get(`${this.baseUrl}/tasks/${taskId}`)
  }

  /**
   * 删除测试表
   */
  async deleteTestTable(data: TestTableDeleteRequest): Promise<{
    message: string
    table: string
    hdfs_data_deleted: boolean
  }> {
    return api.post(`${this.baseUrl}/delete`, data)
  }

  /**
   * 验证测试表
   */
  async verifyTestTable(data: TestTableVerifyRequest): Promise<TestTableVerifyResult> {
    return api.post(`${this.baseUrl}/verify`, data)
  }

  /**
   * 验证测试配置
   */
  async validateConfig(config: ValidationConfig): Promise<ValidationResult> {
    const params = new URLSearchParams()
    Object.entries(config).forEach(([key, value]) => {
      params.append(key, String(value))
    })

    return api.get(`${this.baseUrl}/config/validate?${params.toString()}`)
  }

  /**
   * 获取集群中的测试表
   */
  async getClusterTestTables(clusterId: number): Promise<{
    cluster_id: number
    cluster_name: string
    test_tables: Array<{
      database_name: string
      table_name: string
      partition_count: number
      estimated_files: number
      created_time: string
      size_mb: number
    }>
  }> {
    return api.get(`${this.baseUrl}/cluster/${clusterId}/existing-tables`)
  }
}

// 创建实例
const testTableApi = new TestTableApi()

// Composition API 风格的 hook
export const useTestTableApi = () => {
  return {
    getScenarios: testTableApi.getScenarios.bind(testTableApi),
    createTestTable: testTableApi.createTestTable.bind(testTableApi),
    listTasks: testTableApi.listTasks.bind(testTableApi),
    getTask: testTableApi.getTask.bind(testTableApi),
    deleteTestTable: testTableApi.deleteTestTable.bind(testTableApi),
    verifyTestTable: testTableApi.verifyTestTable.bind(testTableApi),
    validateConfig: testTableApi.validateConfig.bind(testTableApi),
    getClusterTestTables: testTableApi.getClusterTestTables.bind(testTableApi)
  }
}

export default testTableApi
