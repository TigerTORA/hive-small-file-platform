/**
 * API集成测试
 * 测试前端与后端API的集成，数据流转和错误处理
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// 模拟axios
vi.mock('axios', () => {
  const mockGet = vi.fn()
  const mockPost = vi.fn()
  const mockPut = vi.fn()
  const mockDelete = vi.fn()

  return {
    default: {
      create: vi.fn(() => ({
        get: mockGet,
        post: mockPost,
        put: mockPut,
        delete: mockDelete,
        interceptors: {
          request: { use: vi.fn(), eject: vi.fn() },
          response: { use: vi.fn(), eject: vi.fn() }
        }
      })),
      interceptors: {
        request: { use: vi.fn(), eject: vi.fn() },
        response: { use: vi.fn(), eject: vi.fn() }
      }
    },
    mockGet,
    mockPost,
    mockPut,
    mockDelete
  }
})

// 模拟Element Plus消息提示
vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
    warning: vi.fn()
  }
}))

// 导入API (必须在mock之后)
import axios from 'axios'
import { dashboardApi } from '@/api/dashboard'
import { clustersApi } from '@/api/clusters'
import { tablesApi } from '@/api/tables'
import { tasksApi } from '@/api/tasks'

// 获取模拟函数
const mockedAxios = vi.mocked(axios, true)
const { mockGet, mockPost, mockPut, mockDelete } = mockedAxios as any

describe('API Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // axios实例模拟已经在文件顶部设置，这里只需要清理即可
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Dashboard API 集成', () => {
    it('应该正确获取仪表盘数据', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: {
            total_tables: 1500,
            total_small_files: 850000,
            total_size_bytes: 2147483648,
            small_file_ratio: 25.6,
            last_updated: '2024-01-15T10:30:00Z'
          }
        }
      }

      mockGet.mockResolvedValueOnce(mockResponse)

      const result = await dashboardApi.getSummary('cluster-1')

      expect(mockGet).toHaveBeenCalledWith('/summary', {
        params: { cluster_id: 'cluster-1' }
      })
      expect(result).toEqual(mockResponse.data.data)
    })

    it('应该处理API错误响应', async () => {
      const errorResponse = {
        response: {
          status: 500,
          data: {
            success: false,
            error: 'Internal Server Error',
            message: '集群连接失败'
          }
        }
      }

      mockGet.mockRejectedValueOnce(errorResponse)

      await expect(dashboardApi.getSummary('invalid-cluster')).rejects.toThrow()
    })

    it('应该正确获取趋势数据', async () => {
      const mockTrendData = {
        data: {
          success: true,
          data: [
            {
              timestamp: '2024-01-15T09:00:00Z',
              small_files_count: 80000,
              total_size_gb: 1.2
            },
            {
              timestamp: '2024-01-15T10:00:00Z',
              small_files_count: 85000,
              total_size_gb: 1.25
            }
          ]
        }
      }

      mockedAxios.get.mockResolvedValueOnce(mockTrendData)

      const result = await dashboardApi.getTrend('cluster-1', '1h')

      expect(mockGet).toHaveBeenCalledWith('/trend', {
        params: {
          cluster_id: 'cluster-1',
          time_range: '1h'
        }
      })
      expect(result).toEqual(mockTrendData.data.data)
    })
  })

  describe('Clusters API 集成', () => {
    it('应该正确获取集群列表', async () => {
      const mockClusters = {
        data: {
          success: true,
          data: [
            {
              id: 'cluster-1',
              name: '生产集群-01',
              status: 'active',
              namenode_host: '192.168.1.100',
              namenode_port: 9000,
              created_at: '2024-01-01T00:00:00Z'
            },
            {
              id: 'cluster-2',
              name: '测试集群-01',
              status: 'inactive',
              namenode_host: '192.168.1.101',
              namenode_port: 9000,
              created_at: '2024-01-02T00:00:00Z'
            }
          ]
        }
      }

      mockedAxios.get.mockResolvedValueOnce(mockClusters)

      const result = await clustersApi.getAll()

      expect(mockGet).toHaveBeenCalledWith('/clusters')
      expect(result).toEqual(mockClusters.data.data)
      expect(result).toHaveLength(2)
    })

    it('应该正确测试集群连接', async () => {
      const mockConnectionTest = {
        data: {
          success: true,
          data: {
            connected: true,
            latency_ms: 45,
            namenode_version: '3.3.1',
            available_space_gb: 1024.5
          }
        }
      }

      mockPost.mockResolvedValueOnce(mockConnectionTest)

      const testData = {
        namenode_host: '192.168.1.100',
        namenode_port: 9000
      }

      const result = await clustersApi.testConnection(testData)

      expect(mockPost).toHaveBeenCalledWith('/clusters/test-connection', testData)
      expect(result.connected).toBe(true)
      expect(result.latency_ms).toBe(45)
    })

    it('应该处理连接测试失败', async () => {
      const errorResponse = {
        response: {
          status: 400,
          data: {
            success: false,
            error: 'Connection Failed',
            message: '无法连接到指定的NameNode'
          }
        }
      }

      mockPost.mockRejectedValueOnce(errorResponse)

      const testData = {
        namenode_host: '192.168.1.999',
        namenode_port: 9000
      }

      await expect(clustersApi.testConnection(testData)).rejects.toThrow()
    })
  })

  describe('Tables API 集成', () => {
    it('应该正确获取表列表', async () => {
      const mockTables = {
        data: {
          success: true,
          data: {
            tables: [
              {
                cluster_id: 'cluster-1',
                database_name: 'user_data',
                table_name: 'user_profiles',
                total_files: 1500,
                small_files: 850,
                small_file_ratio: 56.7,
                total_size_bytes: 1073741824,
                last_scan_time: '2024-01-15T09:30:00Z'
              },
              {
                cluster_id: 'cluster-1',
                database_name: 'user_data',
                table_name: 'user_activities',
                total_files: 2000,
                small_files: 1200,
                small_file_ratio: 60.0,
                total_size_bytes: 2147483648,
                last_scan_time: '2024-01-15T10:00:00Z'
              }
            ],
            total: 50,
            page: 1,
            page_size: 20
          }
        }
      }

      mockedAxios.get.mockResolvedValueOnce(mockTables)

      const params = {
        cluster_id: 'cluster-1',
        page: 1,
        page_size: 20,
        database_name: 'user_data',
        min_small_file_ratio: 50
      }

      const result = await tablesApi.getAll(params)

      expect(mockGet).toHaveBeenCalledWith('/tables', { params })
      expect(result.tables).toHaveLength(2)
      expect(result.total).toBe(50)
    })

    it('应该正确获取表详情', async () => {
      const mockTableDetail = {
        data: {
          success: true,
          data: {
            basic_info: {
              cluster_id: 'cluster-1',
              database_name: 'user_data',
              table_name: 'user_profiles',
              location: '/user/hive/warehouse/user_data.db/user_profiles',
              owner: 'hive',
              table_type: 'MANAGED_TABLE'
            },
            file_statistics: {
              total_files: 1500,
              small_files: 850,
              small_file_ratio: 56.7,
              total_size_bytes: 1073741824,
              avg_file_size_bytes: 715827,
              median_file_size_bytes: 524288
            },
            file_distribution: [
              { size_range: '0-64KB', file_count: 300, percentage: 20.0 },
              { size_range: '64KB-128KB', file_count: 550, percentage: 36.7 },
              { size_range: '128KB-1MB', file_count: 450, percentage: 30.0 },
              { size_range: '1MB+', file_count: 200, percentage: 13.3 }
            ],
            recent_scans: [
              {
                scan_time: '2024-01-15T10:00:00Z',
                small_files: 850,
                total_files: 1500,
                processing_time_seconds: 45.2
              }
            ]
          }
        }
      }

      mockedAxios.get.mockResolvedValueOnce(mockTableDetail)

      const result = await tablesApi.getDetail('cluster-1', 'user_data', 'user_profiles')

      expect(mockGet).toHaveBeenCalledWith(
        '/tables/cluster-1/user_data/user_profiles'
      )
      expect(result.basic_info.table_name).toBe('user_profiles')
      expect(result.file_statistics.small_file_ratio).toBe(56.7)
    })
  })

  describe('Tasks API 集成', () => {
    it('应该正确获取任务列表', async () => {
      const mockTasks = {
        data: {
          success: true,
          data: {
            tasks: [
              {
                id: 'task-1',
                type: 'scan',
                cluster_id: 'cluster-1',
                database_name: 'user_data',
                table_name: 'user_profiles',
                status: 'completed',
                created_at: '2024-01-15T09:00:00Z',
                completed_at: '2024-01-15T09:05:30Z',
                processing_time_seconds: 330.5
              },
              {
                id: 'task-2',
                type: 'merge',
                cluster_id: 'cluster-1',
                database_name: 'user_data',
                table_name: 'user_activities',
                status: 'running',
                created_at: '2024-01-15T10:00:00Z',
                progress_percentage: 65.4
              }
            ],
            total: 100,
            page: 1,
            page_size: 20
          }
        }
      }

      mockedAxios.get.mockResolvedValueOnce(mockTasks)

      const params = {
        cluster_id: 'cluster-1',
        status: 'all',
        page: 1,
        page_size: 20
      }

      const result = await tasksApi.getAll(params)

      expect(mockGet).toHaveBeenCalledWith('/tasks', { params })
      expect(result.tasks).toHaveLength(2)
      expect(result.tasks[0].status).toBe('completed')
      expect(result.tasks[1].status).toBe('running')
    })

    it('应该正确创建扫描任务', async () => {
      const mockTaskCreation = {
        data: {
          success: true,
          data: {
            task_id: 'task-12345',
            message: '扫描任务已创建',
            estimated_duration_minutes: 15
          }
        }
      }

      mockPost.mockResolvedValueOnce(mockTaskCreation)

      const taskData = {
        cluster_id: 'cluster-1',
        database_name: 'user_data',
        table_name: 'user_profiles',
        small_file_threshold_bytes: 134217728 // 128MB
      }

      const result = await tasksApi.createScanTask(taskData)

      expect(mockPost).toHaveBeenCalledWith('/tasks/scan', taskData)
      expect(result.task_id).toBe('task-12345')
    })

    it('应该正确创建合并任务', async () => {
      const mockMergeCreation = {
        data: {
          success: true,
          data: {
            task_id: 'task-67890',
            message: '合并任务已创建',
            estimated_files_to_merge: 850
          }
        }
      }

      mockPost.mockResolvedValueOnce(mockMergeCreation)

      const mergeData = {
        cluster_id: 'cluster-1',
        database_name: 'user_data',
        table_name: 'user_profiles',
        target_file_size_bytes: 268435456, // 256MB
        max_files_per_merge: 100
      }

      const result = await tasksApi.createMergeTask(mergeData)

      expect(mockPost).toHaveBeenCalledWith('/tasks/merge', mergeData)
      expect(result.task_id).toBe('task-67890')
    })

    it('应该正确获取任务日志', async () => {
      const mockLogs = {
        data: {
          success: true,
          data: {
            logs: [
              {
                timestamp: '2024-01-15T10:00:00Z',
                level: 'INFO',
                message: '开始扫描表 user_data.user_profiles'
              },
              {
                timestamp: '2024-01-15T10:01:30Z',
                level: 'INFO',
                message: '已扫描 500/1500 文件 (33.3%)'
              },
              {
                timestamp: '2024-01-15T10:03:00Z',
                level: 'INFO',
                message: '已扫描 1000/1500 文件 (66.7%)'
              },
              {
                timestamp: '2024-01-15T10:05:30Z',
                level: 'INFO',
                message: '扫描完成，发现 850 个小文件'
              }
            ],
            has_more: false,
            next_cursor: null
          }
        }
      }

      mockedAxios.get.mockResolvedValueOnce(mockLogs)

      const result = await tasksApi.getLogs('task-1', { limit: 100 })

      expect(mockGet).toHaveBeenCalledWith('/tasks/task-1/logs', {
        params: { limit: 100 }
      })
      expect(result.logs).toHaveLength(4)
      expect(result.logs[0].level).toBe('INFO')
    })
  })

  describe('错误处理和重试机制', () => {
    it('应该处理网络错误', async () => {
      const networkError = new Error('Network Error')
      networkError.name = 'NETWORK_ERROR'

      mockGet.mockRejectedValueOnce(networkError)

      await expect(dashboardApi.getSummary('cluster-1')).rejects.toThrow('Network Error')
    })

    it('应该处理超时错误', async () => {
      const timeoutError = new Error('timeout of 5000ms exceeded')
      timeoutError.name = 'TIMEOUT_ERROR'

      mockGet.mockRejectedValueOnce(timeoutError)

      await expect(clustersApi.getAll()).rejects.toThrow('timeout')
    })

    it('应该处理认证错误', async () => {
      const authError = {
        response: {
          status: 401,
          data: {
            success: false,
            error: 'Unauthorized',
            message: '认证令牌已过期'
          }
        }
      }

      mockGet.mockRejectedValueOnce(authError)

      await expect(tablesApi.getAll({ cluster_id: 'cluster-1' })).rejects.toMatchObject({
        response: { status: 401 }
      })
    })

    it('应该处理服务器内部错误', async () => {
      const serverError = {
        response: {
          status: 500,
          data: {
            success: false,
            error: 'Internal Server Error',
            message: '数据库连接失败'
          }
        }
      }

      mockPost.mockRejectedValueOnce(serverError)

      await expect(tasksApi.createScanTask({
        cluster_id: 'cluster-1',
        database_name: 'test',
        table_name: 'test'
      })).rejects.toMatchObject({
        response: { status: 500 }
      })
    })
  })

  describe('性能和并发测试', () => {
    it('应该支持并发API请求', async () => {
      const mockResponses = [
        { data: { success: true, data: { total_tables: 100 } } },
        { data: { success: true, data: { total_tables: 200 } } },
        { data: { success: true, data: { total_tables: 300 } } }
      ]

      mockGet
        .mockResolvedValueOnce(mockResponses[0])
        .mockResolvedValueOnce(mockResponses[1])
        .mockResolvedValueOnce(mockResponses[2])

      const promises = [
        dashboardApi.getSummary('cluster-1'),
        dashboardApi.getSummary('cluster-2'),
        dashboardApi.getSummary('cluster-3')
      ]

      const results = await Promise.all(promises)

      expect(results).toHaveLength(3)
      expect(results[0].total_tables).toBe(100)
      expect(results[1].total_tables).toBe(200)
      expect(results[2].total_tables).toBe(300)
    })

    it('应该在规定时间内完成API调用', async () => {
      const mockResponse = {
        data: {
          success: true,
          data: { total_tables: 1000 }
        }
      }

      mockGet.mockResolvedValueOnce(mockResponse)

      const startTime = performance.now()
      await dashboardApi.getSummary('cluster-1')
      const endTime = performance.now()

      // API调用应该在合理时间内完成（包括mock开销）
      expect(endTime - startTime).toBeLessThan(100)
    })
  })

  describe('数据格式验证', () => {
    it('应该验证API响应数据格式', async () => {
      const validResponse = {
        data: {
          success: true,
          data: {
            total_tables: 1500,
            total_small_files: 850000,
            total_size_bytes: 2147483648,
            small_file_ratio: 25.6,
            last_updated: '2024-01-15T10:30:00Z'
          }
        }
      }

      mockedAxios.get.mockResolvedValueOnce(validResponse)

      const result = await dashboardApi.getSummary('cluster-1')

      // 验证数据类型
      expect(typeof result.total_tables).toBe('number')
      expect(typeof result.total_small_files).toBe('number')
      expect(typeof result.total_size_bytes).toBe('number')
      expect(typeof result.small_file_ratio).toBe('number')
      expect(typeof result.last_updated).toBe('string')

      // 验证数据范围
      expect(result.total_tables).toBeGreaterThan(0)
      expect(result.small_file_ratio).toBeGreaterThanOrEqual(0)
      expect(result.small_file_ratio).toBeLessThanOrEqual(100)
    })

    it('应该处理不完整的响应数据', async () => {
      const incompleteResponse = {
        data: {
          success: true,
          data: {
            total_tables: 1500,
            // 缺少其他必需字段
          }
        }
      }

      mockedAxios.get.mockResolvedValueOnce(incompleteResponse)

      const result = await dashboardApi.getSummary('cluster-1')

      expect(result.total_tables).toBe(1500)
      // 应该能够处理缺失字段
    })
  })
})