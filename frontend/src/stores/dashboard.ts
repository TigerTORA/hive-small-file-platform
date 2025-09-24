import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  dashboardApi,
  type DashboardSummary,
  type TrendPoint,
  type FileDistributionItem,
  type TopTable,
  type RecentTask,
  type ClusterStats
} from '@/api/dashboard'
import { ElMessage } from 'element-plus'

export const useDashboardStore = defineStore('dashboard', () => {
  // 状态
  const summary = ref<DashboardSummary>({
    total_clusters: 0,
    active_clusters: 0,
    total_tables: 0,
    monitored_tables: 0,
    total_files: 0,
    total_small_files: 0,
    small_file_ratio: 0,
    total_size_gb: 0,
    small_file_size_gb: 0
  })

  const trends = ref<TrendPoint[]>([])
  const fileDistribution = ref<FileDistributionItem[]>([])
  const topTables = ref<TopTable[]>([])
  const recentTasks = ref<RecentTask[]>([])
  const clusterStats = ref<ClusterStats[]>([])

  // 加载状态
  const loading = ref({
    summary: false,
    trends: false,
    fileDistribution: false,
    topTables: false,
    recentTasks: false,
    clusterStats: false
  })

  // 错误状态
  const errors = ref({
    summary: null as string | null,
    trends: null as string | null,
    fileDistribution: null as string | null,
    topTables: null as string | null,
    recentTasks: null as string | null,
    clusterStats: null as string | null
  })

  // 计算属性
  const isLoading = computed(() => {
    return Object.values(loading.value).some(l => l)
  })

  const hasErrors = computed(() => {
    return Object.values(errors.value).some(e => e !== null)
  })

  const smallFileRatio = computed(() => {
    if (summary.value.total_files === 0) return 0
    return Math.round((summary.value.total_small_files / summary.value.total_files) * 100)
  })

  // 操作方法
  async function loadSummary(clusterId?: number) {
    loading.value.summary = true
    errors.value.summary = null

    try {
      const data = await dashboardApi.getSummary(clusterId)
      summary.value = data
    } catch (error: any) {
      errors.value.summary = error.message || '加载概要数据失败'
      ElMessage.error('加载概要数据失败')
    } finally {
      loading.value.summary = false
    }
  }

  async function loadTrends(clusterId?: number, days: number = 30) {
    loading.value.trends = true
    errors.value.trends = null

    try {
      const data = await dashboardApi.getTrends(clusterId, days)
      trends.value = data
    } catch (error: any) {
      errors.value.trends = error.message || '加载趋势数据失败'
      ElMessage.error('加载趋势数据失败')
    } finally {
      loading.value.trends = false
    }
  }

  async function loadFileDistribution(clusterId?: number) {
    loading.value.fileDistribution = true
    errors.value.fileDistribution = null

    try {
      const data = await dashboardApi.getFileDistribution(clusterId)
      fileDistribution.value = data
    } catch (error: any) {
      errors.value.fileDistribution = error.message || '加载文件分布数据失败'
      ElMessage.error('加载文件分布数据失败')
    } finally {
      loading.value.fileDistribution = false
    }
  }

  async function loadTopTables(clusterId?: number, limit: number = 10) {
    loading.value.topTables = true
    errors.value.topTables = null

    try {
      const data = await dashboardApi.getTopTables(clusterId, limit)
      topTables.value = data
    } catch (error: any) {
      errors.value.topTables = error.message || '加载TOP表数据失败'
      ElMessage.error('加载TOP表数据失败')
    } finally {
      loading.value.topTables = false
    }
  }

  async function loadRecentTasks(limit: number = 20, status?: string) {
    loading.value.recentTasks = true
    errors.value.recentTasks = null

    try {
      const data = await dashboardApi.getRecentTasks(limit, status)
      recentTasks.value = data
    } catch (error: any) {
      errors.value.recentTasks = error.message || '加载最近任务失败'
      ElMessage.error('加载最近任务失败')
    } finally {
      loading.value.recentTasks = false
    }
  }

  async function loadClusterStats() {
    loading.value.clusterStats = true
    errors.value.clusterStats = null

    try {
      const data = await dashboardApi.getClusterStats()
      clusterStats.value = data.clusters
    } catch (error: any) {
      errors.value.clusterStats = error.message || '加载集群统计失败'
      ElMessage.error('加载集群统计失败')
    } finally {
      loading.value.clusterStats = false
    }
  }

  // 加载所有数据
  async function loadAllData(clusterId?: number) {
    await Promise.all([
      loadSummary(clusterId),
      loadTrends(clusterId, 7), // 默认加载7天数据
      loadFileDistribution(clusterId),
      loadTopTables(clusterId, 10),
      loadRecentTasks(10),
      loadClusterStats()
    ])
  }

  // 刷新数据
  function refresh(clusterId?: number) {
    return loadAllData(clusterId)
  }

  // 清空错误状态
  function clearErrors() {
    Object.keys(errors.value).forEach(key => {
      errors.value[key as keyof typeof errors.value] = null
    })
  }

  // 重置状态
  function reset() {
    summary.value = {
      total_clusters: 0,
      active_clusters: 0,
      total_tables: 0,
      monitored_tables: 0,
      total_files: 0,
      total_small_files: 0,
      small_file_ratio: 0,
      total_size_gb: 0,
      small_file_size_gb: 0
    }
    trends.value = []
    fileDistribution.value = []
    topTables.value = []
    recentTasks.value = []
    clusterStats.value = []
    clearErrors()
  }

  return {
    // 状态
    summary,
    trends,
    fileDistribution,
    topTables,
    recentTasks,
    clusterStats,
    loading,
    errors,

    // 计算属性
    isLoading,
    hasErrors,
    smallFileRatio,

    // 操作方法
    loadSummary,
    loadTrends,
    loadFileDistribution,
    loadTopTables,
    loadRecentTasks,
    loadClusterStats,
    loadAllData,
    refresh,
    clearErrors,
    reset
  }
})
