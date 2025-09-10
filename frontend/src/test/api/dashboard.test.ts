import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { dashboardApi } from '@/api/dashboard'
import type { DashboardSummary, TrendPoint, FileDistributionItem } from '@/api/dashboard'

// Mock the api instance
vi.mock('@/api/index', () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn()
    }
  }
})

// Import the mocked api to get access to the mock
import api from '@/api/index'
const mockApiGet = vi.mocked(api.get)

describe('Dashboard API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('getSummary', () => {
    it('should fetch dashboard summary successfully', async () => {
      const mockSummary: DashboardSummary = {
        total_clusters: 3,
        active_clusters: 2,
        total_tables: 100,
        monitored_tables: 80,
        total_files: 50000,
        total_small_files: 15000,
        small_file_ratio: 30.0,
        total_size_gb: 1000,
        small_file_size_gb: 200
      }

      mockApiGet.mockResolvedValue(mockSummary)

      const result = await dashboardApi.getSummary()

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/summary')
      expect(result).toEqual(mockSummary)
    })

    it('should handle API error', async () => {
      const errorMessage = 'Network Error'
      mockApiGet.mockRejectedValue(new Error(errorMessage))

      await expect(dashboardApi.getSummary()).rejects.toThrow(errorMessage)
    })
  })

  describe('getTrends', () => {
    it('should fetch trends with default parameters', async () => {
      const mockTrends: TrendPoint[] = [
        {
          date: '2023-12-01',
          total_files: 1000,
          small_files: 300,
          ratio: 30.0
        },
        {
          date: '2023-12-02',
          total_files: 1100,
          small_files: 350,
          ratio: 31.8
        }
      ]

      mockApiGet.mockResolvedValue(mockTrends)

      const result = await dashboardApi.getTrends()

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/trends', {
        params: { days: 30 }
      })
      expect(result).toEqual(mockTrends)
    })

    it('should fetch trends with custom parameters', async () => {
      const mockTrends: TrendPoint[] = []
      mockApiGet.mockResolvedValue(mockTrends)

      await dashboardApi.getTrends(1, 7)

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/trends', {
        params: { cluster_id: 1, days: 7 }
      })
    })

    it('should handle trends API error', async () => {
      const errorMessage = 'Server Error'
      mockApiGet.mockRejectedValue(new Error(errorMessage))

      await expect(dashboardApi.getTrends()).rejects.toThrow(errorMessage)
    })
  })

  describe('getFileDistribution', () => {
    it('should fetch file distribution without cluster filter', async () => {
      const mockDistribution: FileDistributionItem[] = [
        { size_range: '< 1MB', count: 1000 },
        { size_range: '1MB-128MB', count: 2000 },
        { size_range: '128MB-1GB', count: 1500 },
        { size_range: '> 1GB', count: 500 }
      ]

      mockApiGet.mockResolvedValue(mockDistribution)

      const result = await dashboardApi.getFileDistribution()

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/file-distribution', {
        params: {}
      })
      expect(result).toEqual(mockDistribution)
    })

    it('should fetch file distribution with cluster filter', async () => {
      const mockDistribution: FileDistributionItem[] = []
      mockApiGet.mockResolvedValue(mockDistribution)

      await dashboardApi.getFileDistribution(1)

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/file-distribution', {
        params: { cluster_id: 1 }
      })
    })
  })

  describe('getTopTables', () => {
    it('should fetch top tables with default limit', async () => {
      const mockTopTables = [
        {
          table_name: 'user_logs',
          small_files: 5000,
          total_files: 8000,
          small_file_ratio: 62.5
        }
      ]

      mockApiGet.mockResolvedValue(mockTopTables)

      const result = await dashboardApi.getTopTables()

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/top-tables', {
        params: { limit: 10 }
      })
      expect(result).toEqual(mockTopTables)
    })

    it('should fetch top tables with custom parameters', async () => {
      const mockTopTables = []
      mockApiGet.mockResolvedValue(mockTopTables)

      await dashboardApi.getTopTables(1, 5)

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/top-tables', {
        params: { cluster_id: 1, limit: 5 }
      })
    })
  })

  describe('getRecentTasks', () => {
    it('should fetch recent tasks with default parameters', async () => {
      const mockRecentTasks = [
        {
          id: 1,
          task_name: 'Merge user_logs',
          table_name: 'user_logs',
          status: 'completed',
          created_time: '2023-12-01T10:00:00Z',
          updated_time: '2023-12-01T11:00:00Z'
        }
      ]

      mockApiGet.mockResolvedValue(mockRecentTasks)

      const result = await dashboardApi.getRecentTasks()

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/recent-tasks', {
        params: { limit: 20 }
      })
      expect(result).toEqual(mockRecentTasks)
    })

    it('should fetch recent tasks with custom parameters', async () => {
      const mockRecentTasks = []
      mockApiGet.mockResolvedValue(mockRecentTasks)

      await dashboardApi.getRecentTasks(5, 'running')

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/recent-tasks', {
        params: { limit: 5, status: 'running' }
      })
    })
  })

  describe('getClusterStats', () => {
    it('should fetch cluster statistics', async () => {
      const mockClusterStats = {
        clusters: [
          {
            id: 1,
            name: 'Production Cluster',
            status: 'active',
            table_count: 50,
            file_count: 25000,
            small_file_ratio: 35.0
          }
        ]
      }

      mockApiGet.mockResolvedValue(mockClusterStats)

      const result = await dashboardApi.getClusterStats()

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/cluster-stats')
      expect(result).toEqual(mockClusterStats)
    })

    it('should handle cluster stats API error', async () => {
      const errorMessage = 'Unauthorized'
      mockApiGet.mockRejectedValue(new Error(errorMessage))

      await expect(dashboardApi.getClusterStats()).rejects.toThrow(errorMessage)
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      const networkError = new Error('Network Error')
      mockApiGet.mockRejectedValue(networkError)

      await expect(dashboardApi.getSummary()).rejects.toThrow('Network Error')
    })

    it('should handle HTTP error responses', async () => {
      const httpError = {
        response: {
          status: 500,
          data: { message: 'Internal Server Error' }
        }
      }
      mockApiGet.mockRejectedValue(httpError)

      await expect(dashboardApi.getSummary()).rejects.toEqual(httpError)
    })

    it('should handle timeout errors', async () => {
      const timeoutError = new Error('timeout of 5000ms exceeded')
      mockApiGet.mockRejectedValue(timeoutError)

      await expect(dashboardApi.getTrends()).rejects.toThrow('timeout of 5000ms exceeded')
    })
  })

  describe('Request Configuration', () => {
    it('should send requests with correct base URL', async () => {
      mockApiGet.mockResolvedValue({})

      await dashboardApi.getSummary()

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/summary')
    })

    it('should handle query parameters correctly', async () => {
      mockApiGet.mockResolvedValue([])

      await dashboardApi.getTrends(5, 14)

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/trends', {
        params: { cluster_id: 5, days: 14 }
      })
    })

    it('should omit undefined parameters', async () => {
      mockApiGet.mockResolvedValue([])

      await dashboardApi.getTopTables(undefined, 15)

      expect(mockApiGet).toHaveBeenCalledWith('/dashboard/top-tables', {
        params: { limit: 15 }
      })
    })
  })

  describe('Response Data Types', () => {
    it('should return correctly typed summary data', async () => {
      const mockSummary: DashboardSummary = {
        total_clusters: 1,
        active_clusters: 1,
        total_tables: 10,
        monitored_tables: 8,
        total_files: 1000,
        total_small_files: 300,
        small_file_ratio: 30,
        total_size_gb: 100,
        small_file_size_gb: 20
      }

      mockApiGet.mockResolvedValue(mockSummary)

      const result = await dashboardApi.getSummary()

      expect(typeof result.total_clusters).toBe('number')
      expect(typeof result.active_clusters).toBe('number')
      expect(typeof result.small_file_ratio).toBe('number')
      expect(result.total_clusters).toBe(1)
      expect(result.small_file_ratio).toBe(30)
    })

    it('should return correctly typed trend data', async () => {
      const mockTrends: TrendPoint[] = [
        {
          date: '2023-12-01',
          total_files: 1000,
          small_files: 300,
          ratio: 30.0
        }
      ]

      mockApiGet.mockResolvedValue(mockTrends)

      const result = await dashboardApi.getTrends()

      expect(Array.isArray(result)).toBe(true)
      expect(result[0]).toHaveProperty('date')
      expect(result[0]).toHaveProperty('total_files')
      expect(result[0]).toHaveProperty('small_files')
      expect(result[0]).toHaveProperty('ratio')
      expect(typeof result[0].date).toBe('string')
      expect(typeof result[0].total_files).toBe('number')
    })
  })
})