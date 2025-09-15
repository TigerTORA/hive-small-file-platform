/**
 * 集群API测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { clustersApi } from '@/api/clusters'

// Mock axios
vi.mock('axios')
const mockedAxios = vi.mocked(axios)

describe('集群API测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getClusters', () => {
    it('应该成功获取集群列表', async () => {
      const mockClusters = [
        {
          id: 1,
          name: 'test-cluster-1',
          hive_metastore_url: 'mysql://test:test@localhost:3306/hive',
          hdfs_namenode_url: 'hdfs://localhost:9000',
          connection_type: 'mysql',
          is_active: true
        },
        {
          id: 2,
          name: 'test-cluster-2',
          hive_metastore_url: 'mysql://test:test@localhost:3307/hive',
          hdfs_namenode_url: 'hdfs://localhost:9001',
          connection_type: 'mysql',
          is_active: false
        }
      ]

      mockedAxios.get.mockResolvedValue({ data: mockClusters })

      const result = await clustersApi.list()

      expect(mockedAxios.get).toHaveBeenCalledWith('/clusters/')
      expect(result).toEqual(mockClusters)
    })

    it('应该处理获取集群列表失败的情况', async () => {
      const errorMessage = 'Network Error'
      mockedAxios.get.mockRejectedValue(new Error(errorMessage))

      await expect(clustersApi.list()).rejects.toThrow(errorMessage)
    })
  })

  describe('createCluster', () => {
    it('应该成功创建集群', async () => {
      const newCluster = {
        name: 'new-cluster',
        hive_metastore_url: 'mysql://test:test@localhost:3306/hive',
        hdfs_namenode_url: 'hdfs://localhost:9000',
        connection_type: 'mysql' as const
      }

      const createdCluster = {
        id: 3,
        ...newCluster,
        is_active: true,
        created_time: '2023-01-01T00:00:00Z'
      }

      mockedAxios.post.mockResolvedValue({ data: createdCluster })

      const result = await clustersApi.create(newCluster)

      expect(mockedAxios.post).toHaveBeenCalledWith('/clusters/', newCluster)
      expect(result).toEqual(createdCluster)
    })

    it('应该处理创建集群验证错误', async () => {
      const invalidCluster = {
        name: '',
        hive_metastore_url: 'invalid-url',
        hdfs_namenode_url: '',
        connection_type: 'mysql' as const
      }

      const validationError = {
        response: {
          status: 422,
          data: {
            detail: [
              { field: 'name', message: 'Name is required' },
              { field: 'hdfs_namenode_url', message: 'Invalid URL' }
            ]
          }
        }
      }

      mockedAxios.post.mockRejectedValue(validationError)

      await expect(clustersApi.create(invalidCluster)).rejects.toMatchObject(validationError)
    })
  })

  describe('updateCluster', () => {
    it('应该成功更新集群', async () => {
      const clusterId = 1
      const updateData = {
        name: 'updated-cluster',
        is_active: false
      }

      const updatedCluster = {
        id: clusterId,
        name: 'updated-cluster',
        hive_metastore_url: 'mysql://test:test@localhost:3306/hive',
        hdfs_namenode_url: 'hdfs://localhost:9000',
        connection_type: 'mysql',
        is_active: false,
        updated_time: '2023-01-01T12:00:00Z'
      }

      mockedAxios.put.mockResolvedValue({ data: updatedCluster })

      const result = await clustersApi.update(clusterId, updateData)

      expect(mockedAxios.put).toHaveBeenCalledWith(`/clusters/${clusterId}`, updateData)
      expect(result).toEqual(updatedCluster)
    })
  })

  describe('deleteCluster', () => {
    it('应该成功删除集群', async () => {
      const clusterId = 1
      mockedAxios.delete.mockResolvedValue({ status: 204 })

      await clustersApi.delete(clusterId)

      expect(mockedAxios.delete).toHaveBeenCalledWith(`/clusters/${clusterId}`)
    })

    it('应该处理删除不存在的集群', async () => {
      const clusterId = 999
      const notFoundError = {
        response: {
          status: 404,
          data: { detail: 'Cluster not found' }
        }
      }

      mockedAxios.delete.mockRejectedValue(notFoundError)

      await expect(clustersApi.delete(clusterId)).rejects.toMatchObject(notFoundError)
    })
  })

  describe('testConnection', () => {
    it('应该成功测试集群连接', async () => {
      const clusterId = 1
      const connectionResult = {
        hive_connection: { status: 'success', message: 'Connected' },
        hdfs_connection: { status: 'success', message: 'Connected' },
        overall_status: 'healthy'
      }

      mockedAxios.post.mockResolvedValue({ data: connectionResult })

      const result = await clustersApi.testConnection(clusterId)

      expect(mockedAxios.post).toHaveBeenCalledWith(`/clusters/${clusterId}/test`)
      expect(result).toEqual(connectionResult)
    })

    it('应该处理连接测试失败', async () => {
      const clusterId = 1
      const connectionResult = {
        hive_connection: { status: 'error', message: 'Connection timeout' },
        hdfs_connection: { status: 'success', message: 'Connected' },
        overall_status: 'unhealthy'
      }

      mockedAxios.post.mockResolvedValue({ data: connectionResult })

      const result = await clustersApi.testConnection(clusterId)

      expect(result.overall_status).toBe('unhealthy')
      expect(result.hive_connection.status).toBe('error')
    })
  })

  describe('错误处理', () => {
    it('应该正确处理网络错误', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Network Error'))

      await expect(clustersApi.list()).rejects.toThrow('Network Error')
    })

    it('应该正确处理服务器错误', async () => {
      const serverError = {
        response: {
          status: 500,
          data: { detail: 'Internal Server Error' }
        }
      }

      mockedAxios.get.mockRejectedValue(serverError)

      await expect(clustersApi.list()).rejects.toMatchObject(serverError)
    })

    it('应该正确处理认证错误', async () => {
      const authError = {
        response: {
          status: 401,
          data: { detail: 'Authentication required' }
        }
      }

      mockedAxios.get.mockRejectedValue(authError)

      await expect(clustersApi.list()).rejects.toMatchObject(authError)
    })
  })
})