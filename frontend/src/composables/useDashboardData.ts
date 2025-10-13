import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useMonitoringStore } from '@/stores/monitoring'
import {
  dashboardApi,
  type FileClassificationItem,
  type EnhancedColdnessDistribution,
  type TopTable,
  type ColdDataItem,
  type DashboardSummary,
  type FormatCompressionItem
} from '@/api/dashboard'

export function useDashboardData() {
  const monitoringStore = useMonitoringStore()
  const selectedClusterId = computed(() => monitoringStore.settings.selectedCluster)
  const isLoadingCharts = ref(false)
  const renderError = ref<string | null>(null)
  let activeRequestId = 0

  // 原始数据状态
  const fileClassificationItems = ref<FileClassificationItem[]>([])
  const coldnessDistribution = ref<EnhancedColdnessDistribution | null>(null)
  const formatCompressionItems = ref<FormatCompressionItem[]>([])
  const topTables = ref<TopTable[]>([])
  const coldestData = ref<ColdDataItem[]>([])
  const dashboardSummary = ref<DashboardSummary | null>(null)

  // 文件分类数据转换为饼状图数据
  const fileClassificationData = computed(() => {
    return fileClassificationItems.value.map(item => ({
      name: item.category,
      value: item.count,
      description: item.description,
      details: {
        count: item.count,
        size_gb: item.size_gb
      }
    }))
  })

  // 文件分类总数
  const fileClassificationTotal = computed(() => {
    return fileClassificationItems.value.reduce((sum, item) => sum + item.count, 0)
  })

  // 冷数据分布数据转换为饼状图数据(5档)
  const coldnessDistributionData = computed(() => {
    if (!coldnessDistribution.value) return []

    const dist = coldnessDistribution.value.distribution

    // 合并为5个时间段
    const merged = {
      recent: {
        name: '1-7天',
        total_size_gb: (dist.within_1_day?.total_size_gb || 0) + (dist.day_1_to_7?.total_size_gb || 0),
        partitions: {
          count: (dist.within_1_day?.partitions?.count || 0) + (dist.day_1_to_7?.partitions?.count || 0),
          size_gb: (dist.within_1_day?.partitions?.size_gb || 0) + (dist.day_1_to_7?.partitions?.size_gb || 0)
        },
        tables: {
          count: (dist.within_1_day?.tables?.count || 0) + (dist.day_1_to_7?.tables?.count || 0),
          size_gb: (dist.within_1_day?.tables?.size_gb || 0) + (dist.day_1_to_7?.tables?.size_gb || 0)
        }
      },
      month: {
        name: '1周-1月',
        total_size_gb: dist.week_1_to_month?.total_size_gb || 0,
        partitions: dist.week_1_to_month?.partitions || { count: 0, size_gb: 0 },
        tables: dist.week_1_to_month?.tables || { count: 0, size_gb: 0 }
      },
      quarter: {
        name: '1-6月',
        total_size_gb: (dist.month_1_to_3?.total_size_gb || 0) + (dist.month_3_to_6?.total_size_gb || 0),
        partitions: {
          count: (dist.month_1_to_3?.partitions?.count || 0) + (dist.month_3_to_6?.partitions?.count || 0),
          size_gb: (dist.month_1_to_3?.partitions?.size_gb || 0) + (dist.month_3_to_6?.partitions?.size_gb || 0)
        },
        tables: {
          count: (dist.month_1_to_3?.tables?.count || 0) + (dist.month_3_to_6?.tables?.count || 0),
          size_gb: (dist.month_1_to_3?.tables?.size_gb || 0) + (dist.month_3_to_6?.tables?.size_gb || 0)
        }
      },
      year: {
        name: '6-12月',
        total_size_gb: dist.month_6_to_12?.total_size_gb || 0,
        partitions: dist.month_6_to_12?.partitions || { count: 0, size_gb: 0 },
        tables: dist.month_6_to_12?.tables || { count: 0, size_gb: 0 }
      },
      old: {
        name: '1年以上',
        total_size_gb: (dist.year_1_to_3?.total_size_gb || 0) + (dist.over_3_years?.total_size_gb || 0),
        partitions: {
          count: (dist.year_1_to_3?.partitions?.count || 0) + (dist.over_3_years?.partitions?.count || 0),
          size_gb: (dist.year_1_to_3?.partitions?.size_gb || 0) + (dist.over_3_years?.partitions?.size_gb || 0)
        },
        tables: {
          count: (dist.year_1_to_3?.tables?.count || 0) + (dist.over_3_years?.tables?.count || 0),
          size_gb: (dist.year_1_to_3?.tables?.size_gb || 0) + (dist.over_3_years?.tables?.size_gb || 0)
        }
      }
    }

    return Object.values(merged).map(item => ({
      name: item.name,
      value: item.total_size_gb,
      details: {
        partitions: item.partitions,
        tables: item.tables
      }
    }))
  })

  // 冷数据总大小
  const coldDataTotal = computed(() => {
    return coldnessDistributionData.value.reduce((sum, item) => sum + item.value, 0)
  })

  // 组合格式数据转换为饼状图数据
  const formatCompressionData = computed(() => {
    return formatCompressionItems.value.map(item => {
      // 简化图例显示文字
      let shortName = item.format_combination
        .replace('(无压缩)', '·无压缩')
        .replace('(ZLIB压缩)', '·ZLIB')
        .replace('(SNAPPY压缩)', '·SNAPPY')
        .replace('(GZIP压缩)', '·GZIP')
        .replace('(LZ4压缩)', '·LZ4')

      return {
        name: shortName,
        value: item.table_count,
        description: `${item.format_combination}`,
        details: {
          table_count: item.table_count,
          total_size_gb: item.total_size_gb,
          small_files: item.small_files,
          total_files: item.total_files,
          percentage: item.percentage,
          original_name: item.format_combination
        }
      }
    })
  })

  // 组合格式总表数
  const formatCompressionTotal = computed(() => {
    return formatCompressionItems.value.reduce((sum, item) => sum + item.table_count, 0)
  })

  // 加载图表数据
  const loadChartData = async (clusterIdOverride?: number | null) => {
    const requestId = ++activeRequestId
    const clusterId = clusterIdOverride ?? selectedClusterId.value ?? undefined
    isLoadingCharts.value = true
    renderError.value = null
    try {
      const [
        fileClassificationResult,
        coldnessResult,
        formatCompressionResult,
        topTablesResult,
        coldestDataResult,
        summaryResult
      ] = await Promise.all([
        dashboardApi.getFileClassification(clusterId),
        dashboardApi.getEnhancedColdnessDistribution(clusterId),
        dashboardApi.getFormatCompressionDistribution(clusterId),
        dashboardApi.getTopTables(clusterId, 10),
        dashboardApi.getColdestData(10),
        dashboardApi.getSummary(clusterId)
      ])

      if (requestId !== activeRequestId) {
        return
      }

      fileClassificationItems.value = fileClassificationResult
      coldnessDistribution.value = coldnessResult
      formatCompressionItems.value = formatCompressionResult
      topTables.value = topTablesResult
      coldestData.value = coldestDataResult
      dashboardSummary.value = summaryResult
    } catch (error: any) {
      if (requestId === activeRequestId) {
        renderError.value = error?.message || '加载图表数据失败'
        ElMessage.error(renderError.value)
      }
      throw error
    } finally {
      if (requestId === activeRequestId) {
        isLoadingCharts.value = false
      }
    }
  }

  // 刷新图表数据
  const refreshChartData = async () => {
    await loadChartData(selectedClusterId.value ?? undefined)
    ElMessage.success('图表数据已刷新')
  }

  // 监听集群变化
  watch(
    () => monitoringStore.settings.selectedCluster,
    async (cid) => {
      await loadChartData(cid ?? undefined)
    },
    { immediate: true }
  )

  return {
    // 状态
    selectedClusterId,
    isLoadingCharts,
    renderError,

    // 原始数据
    fileClassificationItems,
    coldnessDistribution,
    formatCompressionItems,
    topTables,
    coldestData,
    dashboardSummary,

    // 计算数据
    fileClassificationData,
    fileClassificationTotal,
    coldnessDistributionData,
    coldDataTotal,
    formatCompressionData,
    formatCompressionTotal,

    // 方法
    loadChartData,
    refreshChartData
  }
}
