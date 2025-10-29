import axios, { AxiosInstance } from 'axios'
import dotenv from 'dotenv'
import path from 'path'

dotenv.config({ path: path.resolve(__dirname, '../../.env') })

/**
 * API客户端工具类
 * 用于调用后端API并验证数据一致性
 */
export class ApiClient {
  private client: AxiosInstance

  constructor() {
    const baseURL = process.env.BACKEND_API_URL || 'http://localhost:8000'
    this.client = axios.create({
      baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  /**
   * 获取集群列表
   */
  async getClusters() {
    try {
      const response = await this.client.get('/api/v1/clusters/')
      return response.data
    } catch (error) {
      console.error('获取集群列表失败:', error)
      throw error
    }
  }

  /**
   * 获取指定集群的表列表
   */
  async getTables(clusterId: string, database: string = 'default') {
    try {
      const response = await this.client.get('/api/v1/tables/', {
        params: { cluster_id: clusterId, database },
      })
      return response.data
    } catch (error) {
      console.error('获取表列表失败:', error)
      throw error
    }
  }

  /**
   * 获取表详情
   */
  async getTableDetail(clusterId: string, database: string, tableName: string) {
    try {
      const response = await this.client.get('/api/v1/tables/table-detail/', {
        params: {
          cluster_id: clusterId,
          database,
          table: tableName,
        },
      })
      return response.data
    } catch (error) {
      console.error('获取表详情失败:', error)
      throw error
    }
  }

  /**
   * 获取任务列表
   */
  async getTasks() {
    try {
      const response = await this.client.get('/api/v1/scan-tasks/')
      return response.data
    } catch (error) {
      console.error('获取任务列表失败:', error)
      throw error
    }
  }

  /**
   * 获取指定任务的详细信息
   */
  async getTaskDetail(taskId: string) {
    try {
      const response = await this.client.get(`/api/tasks/${taskId}`)
      return response.data
    } catch (error) {
      console.error('获取任务详情失败:', error)
      throw error
    }
  }

  /**
   * 触发小文件合并任务
   */
  async triggerMerge(
    clusterId: string,
    database: string,
    tableName: string,
    hdfsPath: string
  ) {
    try {
      const response = await this.client.post('/api/v1/merge/', {
        cluster_id: clusterId,
        database,
        table: tableName,
        hdfs_path: hdfsPath,
      })
      return response.data
    } catch (error) {
      console.error('触发合并任务失败:', error)
      throw error
    }
  }

  /**
   * 验证UI数据与API数据是否一致
   */
  async validateData(
    uiData: any,
    apiEndpoint: string,
    params?: any,
    compareFn?: (ui: any, api: any) => boolean
  ): Promise<{ isValid: boolean; message: string; details?: any }> {
    try {
      const response = await this.client.get(apiEndpoint, { params })
      const apiData = response.data

      // 如果提供了自定义比较函数，使用自定义函数
      if (compareFn) {
        const isValid = compareFn(uiData, apiData)
        return {
          isValid,
          message: isValid ? '数据验证通过' : '数据不一致',
          details: { uiData, apiData },
        }
      }

      // 默认简单比较
      const isValid = JSON.stringify(uiData) === JSON.stringify(apiData)
      return {
        isValid,
        message: isValid ? '数据验证通过' : '数据不一致',
        details: { uiData, apiData },
      }
    } catch (error) {
      return {
        isValid: false,
        message: `API调用失败: ${error}`,
        details: { error },
      }
    }
  }

  /**
   * 等待任务完成
   * @param taskId 任务ID
   * @param timeout 超时时间（毫秒）
   * @param pollInterval 轮询间隔（毫秒）
   */
  async waitForTaskCompletion(
    taskId: string,
    timeout: number = 300000,
    pollInterval: number = 2000
  ): Promise<any> {
    const startTime = Date.now()

    while (Date.now() - startTime < timeout) {
      try {
        const task = await this.getTaskDetail(taskId)

        // 任务完成状态
        if (task.status === 'completed' || task.status === 'success') {
          return task
        }

        // 任务失败状态
        if (task.status === 'failed' || task.status === 'error') {
          throw new Error(`任务失败: ${task.error_message || '未知错误'}`)
        }

        // 等待下一次轮询
        await new Promise(resolve => setTimeout(resolve, pollInterval))
      } catch (error) {
        console.error('轮询任务状态失败:', error)
        throw error
      }
    }

    throw new Error(`任务超时: ${taskId}`)
  }
}
