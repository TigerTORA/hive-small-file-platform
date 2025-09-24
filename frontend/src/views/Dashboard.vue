<template>
  <div class="dashboard">
    <el-alert
      v-if="renderError"
      :title="'监控中心加载失败：' + renderError"
      type="error"
      show-icon
      style="margin-bottom: 12px"
    />
    <!-- 顶部概览统计卡片区域 -->
    <div class="overview-stats">
      <div class="stat-card" v-loading="isLoadingCharts">
        <div class="stat-icon">
          <el-icon><Files /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ dashboardSummary?.total_files?.toLocaleString() || '-' }}</div>
          <div class="stat-label">总文件数</div>
        </div>
      </div>

      <div class="stat-card" v-loading="isLoadingCharts">
        <div class="stat-icon small-files">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ dashboardSummary?.small_file_ratio?.toFixed(1) || '-' }}%</div>
          <div class="stat-label">小文件比例</div>
        </div>
      </div>

      <div class="stat-card" v-loading="isLoadingCharts">
        <div class="stat-icon storage">
          <el-icon><Coin /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ dashboardSummary?.total_size_gb?.toFixed(2) || '-' }}GB</div>
          <div class="stat-label">总存储空间</div>
        </div>
      </div>

      <div class="stat-card" v-loading="isLoadingCharts">
        <div class="stat-icon clusters">
          <el-icon><Monitor /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ dashboardSummary?.monitored_tables?.toLocaleString() || '-' }}</div>
          <div class="stat-label">监控表数</div>
        </div>
      </div>
    </div>

    <!-- 四饼状图布局 -->
    <div class="pie-charts-section">

      <!-- 三饼状图容器 -->
      <div class="triple-pie-charts">
        <!-- 小文件分析饼状图 -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>
              <el-icon><Files /></el-icon>
              小文件分析
            </h3>
            <el-tag size="small" type="primary">
              总文件：{{ fileClassificationTotal.toLocaleString() }}
            </el-tag>
          </div>
          <div class="chart-content">
            <PieChart
              :data="fileClassificationData"
              :height="380"
              :color-scheme="compressionColorScheme"
              @sector-click="onFileClassificationClick"
            />
          </div>
        </div>

        <!-- 最后访问时间分布饼状图 -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>
              <el-icon><Clock /></el-icon>
              最后访问时间分布
            </h3>
            <el-tag size="small" type="primary">
              总大小：{{ coldDataTotal.toFixed(2) }}GB
            </el-tag>
          </div>
          <div class="chart-content">
            <PieChart
              :data="coldnessDistributionData"
              :height="380"
              :color-scheme="coldnessColorScheme"
              :tooltip-formatter="formatColdnessTooltip"
              @sector-click="onColdnessDistributionClick"
            />
          </div>
        </div>

        <!-- 存储&压缩格式组合分布饼状图 -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>
              <el-icon><Setting /></el-icon>
              存储&压缩格式分布
            </h3>
            <el-tag size="small" type="primary">
              总表数：{{ formatCompressionTotal.toLocaleString() }}
            </el-tag>
          </div>
          <div class="chart-content">
            <PieChart
              :data="formatCompressionData"
              :height="380"
              :color-scheme="formatCompressionColorScheme"
              :tooltip-formatter="formatCompressionTooltip"
              @sector-click="onFormatCompressionClick"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 排行榜区域 -->
    <div class="rankings-section">

      <!-- 双排行榜容器 -->
      <div class="dual-rankings">
          <!-- 问题表排行榜 -->
          <div class="ranking-card">
            <div class="ranking-header">
              <h3>
                <el-icon><Warning /></el-icon>
                问题表排行榜
              </h3>
              <el-tag size="small" type="danger">
                小文件最多TOP10
              </el-tag>
            </div>
            <div class="ranking-content">
            <el-table
              :data="topTables"
              size="small"
              :show-header="true"
              max-height="300"
            >
              <el-table-column prop="cluster_name" label="集群" width="80" />
              <el-table-column prop="database_name" label="数据库" width="120" />
              <el-table-column prop="table_name" label="表名" min-width="150" show-overflow-tooltip />
              <el-table-column label="小文件数" width="100" align="right">
                <template #default="scope">
                  <el-text type="danger" size="small">
                    {{ scope.row.small_files.toLocaleString() }}
                  </el-text>
                </template>
              </el-table-column>
              <el-table-column label="占比" width="80" align="right">
                <template #default="scope">
                  <el-text size="small">
                    {{ scope.row.small_file_ratio.toFixed(1) }}%
                  </el-text>
                </template>
              </el-table-column>
              <el-table-column label="大小" width="90" align="right">
                <template #default="scope">
                  <el-text size="small">
                    {{ scope.row.total_size_gb.toFixed(2) }}GB
                  </el-text>
                </template>
              </el-table-column>
            </el-table>
            </div>
          </div>

          <!-- 冷数据排行榜 -->
          <div class="ranking-card">
            <div class="ranking-header">
              <h3>
                <el-icon><Timer /></el-icon>
                冷数据排行榜
              </h3>
              <el-tag size="small" type="info">
                最久未访问TOP10
              </el-tag>
            </div>
            <div class="ranking-content">
              <el-table
                :data="coldestData"
                size="small"
                :show-header="true"
                max-height="300"
              >
                <el-table-column prop="cluster_name" label="集群" width="80" />
                <el-table-column prop="database_name" label="数据库" width="120" />
                <el-table-column prop="table_name" label="表名" min-width="150" show-overflow-tooltip />
                <el-table-column label="未访问天数" width="100" align="right">
                  <template #default="scope">
                    <el-text type="warning" size="small">
                      {{ scope.row.days_since_last_access }}天
                    </el-text>
                  </template>
                </el-table-column>
                <el-table-column label="大小" width="90" align="right">
                  <template #default="scope">
                    <el-text size="small">
                      {{ scope.row.total_size_gb.toFixed(2) }}GB
                    </el-text>
                  </template>
                </el-table-column>
                <el-table-column label="文件数" width="80" align="right">
                  <template #default="scope">
                    <el-text size="small">
                      {{ scope.row.file_count }}
                    </el-text>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
    </div>

  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref, watch, nextTick } from 'vue'
  import {
    Refresh,
    PieChart as PieChartIcon,
    Files,
    Clock,
    TrendCharts,
    Warning,
    Timer,
    Coin,
    Monitor,
    List,
    DataAnalysis,
    Setting
  } from '@element-plus/icons-vue'
  import { ElMessage } from 'element-plus'
  import { useMonitoringStore } from '@/stores/monitoring'
  import { clustersApi } from '@/api/clusters'
  import PieChart from '@/components/charts/PieChart.vue'
  import { dashboardApi, type FileClassificationItem, type EnhancedColdnessDistribution, type TopTable, type ColdDataItem, type DashboardSummary, type RecentTask, type FileDistributionItem, type TrendPoint, type StorageFormatItem, type CompressionFormatItem, type FormatCompressionItem } from '@/api/dashboard'

  // 四饼状图相关数据
  const monitoringStore = useMonitoringStore()
  const selectedClusterId = ref<number | null>(monitoringStore.settings.selectedCluster)
  const renderError = ref<string | null>(null)
  const isLoadingCharts = ref(false)
  const fileClassificationItems = ref<FileClassificationItem[]>([])
  const coldnessDistribution = ref<EnhancedColdnessDistribution | null>(null)
  const formatCompressionItems = ref<FormatCompressionItem[]>([])
  const topTables = ref<TopTable[]>([])
  const coldestData = ref<ColdDataItem[]>([])
  const dashboardSummary = ref<DashboardSummary | null>(null)
  const recentTasks = ref<RecentTask[]>([])
  const fileDistribution = ref<FileDistributionItem[]>([])
  const trendData = ref<TrendPoint[]>([])
  const trendChartRef = ref<HTMLCanvasElement>()

  // 简单的集群列表
  const availableClusters = ref([
    { id: 1, name: 'CDP-14' },
    { id: 2, name: 'CDP-15' },
    { id: 3, name: 'CDP-16' }
  ])

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

  // 冷数据分布数据转换为饼状图数据（5档）
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
    })) // 显示所有时间段，包括0值的
  })

  // 冷数据总大小
  const coldDataTotal = computed(() => {
    return coldnessDistributionData.value.reduce((sum, item) => sum + item.value, 0)
  })

  // 存储格式数据转换为饼状图数据
  const storageFormatData = computed(() => {
    return storageFormatItems.value.map(item => ({
      name: item.format_name,
      value: item.table_count,
      description: `${item.format_name} 格式`,
      details: {
        table_count: item.table_count,
        total_size_gb: item.total_size_gb,
        small_files: item.small_files,
        total_files: item.total_files,
        percentage: item.percentage
      }
    }))
  })

  // 存储格式总表数
  const storageFormatTotal = computed(() => {
    return storageFormatItems.value.reduce((sum, item) => sum + item.table_count, 0)
  })

  // 压缩格式数据转换为饼状图数据
  const compressionFormatData = computed(() => {
    return compressionFormatItems.value.map(item => ({
      name: item.compression_name,
      value: item.table_count,
      description: `${item.compression_name} 压缩`,
      details: {
        table_count: item.table_count,
        total_size_gb: item.total_size_gb,
        small_files: item.small_files,
        total_files: item.total_files,
        percentage: item.percentage
      }
    }))
  })

  // 压缩格式总表数
  const compressionFormatTotal = computed(() => {
    return compressionFormatItems.value.reduce((sum, item) => sum + item.table_count, 0)
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

  // 颜色配置
  const compressionColorScheme = [
    '#5470c6', // 可压缩小文件
    '#ee6666', // ACID表小文件
    '#fac858', // 单分区文件
    '#91cc75', // 数据湖表文件
    '#73c0de', // 其他
    '#3ba272',
    '#fc8452',
    '#9a60b4'
  ]

  const compressionFormatColorScheme = [
    '#8C8C8C', // NONE - 灰色
    '#1890FF', // ZLIB - 蓝色
    '#52C41A', // SNAPPY - 绿色
    '#FAAD14', // GZIP - 橙色
    '#722ED1', // LZ4 - 紫色
    '#EB2F96', // BZIP2 - 品红
    '#13C2C2', // DEFLATE - 青色
    '#FA8C16'  // OTHER - 橘色
  ]

  const coldnessColorScheme = [
    '#67C23A', // 1-7天 - 绿色
    '#E6A23C', // 1周-1月 - 橙色
    '#F56C6C', // 1-6月 - 红色
    '#409EFF', // 6-12月 - 蓝色
    '#909399'  // 1年以上 - 灰色
  ]

  const formatCompressionColorScheme = [
    '#faad14', // TEXT(无压缩) - 橙色
    '#52c41a', // ORC(ZLIB压缩) - 绿色
    '#2f54eb', // PARQUET(SNAPPY压缩) - 蓝色
    '#722ed1', // OTHER(无压缩) - 紫色
    '#eb2f96', // 其他组合 - 品红
    '#13c2c2', // 青色
    '#fa8c16', // 橘色
    '#a0d911'  // 青绿色
  ]

  // 冷数据饼状图提示框格式化
  const formatColdnessTooltip = (item: any) => {
    const details = item.details
    if (!details) return ''

    return `
      <div style="font-weight: bold; margin-bottom: 8px;">${item.name}</div>
      <div>📊 分区：${details.partitions.count}个 (${details.partitions.size_gb.toFixed(2)}GB)</div>
      <div>📋 表：${details.tables.count}个 (${details.tables.size_gb.toFixed(2)}GB)</div>
      <div style="margin-top: 4px; font-weight: bold;">💾 总计：${item.value.toFixed(2)}GB</div>
    `
  }

  // 存储格式饼状图提示框格式化
  const formatStorageFormatTooltip = (item: any) => {
    const details = item.details
    if (!details) return ''

    const smallFileRatio = details.total_files > 0 ? (details.small_files / details.total_files * 100).toFixed(1) : '0'

    return `
      <div style="font-weight: bold; margin-bottom: 8px;">${item.name} 格式</div>
      <div>📊 表数量：${details.table_count}个 (${details.percentage}%)</div>
      <div>📁 总文件：${details.total_files.toLocaleString()}个</div>
      <div>⚠️ 小文件：${details.small_files.toLocaleString()}个 (${smallFileRatio}%)</div>
      <div style="margin-top: 4px; font-weight: bold;">💾 总大小：${details.total_size_gb.toFixed(2)}GB</div>
    `
  }

  // 组合格式tooltip格式化函数
  const formatCompressionTooltip = (item: any) => {
    const details = item.details
    if (!details) return ''

    const smallFileRatio = details.total_files > 0 ? (details.small_files / details.total_files * 100).toFixed(1) : '0'

    return `
      <div style="font-weight: bold; margin-bottom: 8px;">${item.name}</div>
      <div>📊 表数量：${details.table_count}个 (${details.percentage}%)</div>
      <div>📁 总文件：${details.total_files.toLocaleString()}个</div>
      <div>⚠️ 小文件：${details.small_files.toLocaleString()}个 (${smallFileRatio}%)</div>
      <div style="margin-top: 4px; font-weight: bold;">💾 总大小：${details.total_size_gb.toFixed(2)}GB</div>
    `
  }

  // 存储格式点击处理
  const onStorageFormatClick = (item: any) => {
    console.log('点击存储格式:', item)
    // 可以添加跳转到表管理页面等逻辑
  }

  // 压缩格式点击处理
  const onCompressionFormatClick = (item: any) => {
    console.log('点击压缩格式:', item)
    // 可以添加跳转到表管理页面等逻辑
  }

  // 组合格式点击处理
  const onFormatCompressionClick = (item: any) => {
    console.log('点击组合格式:', item)
    // 可以添加跳转到表管理页面等逻辑
  }


  // 加载四饼状图数据
  const loadChartData = async () => {
    isLoadingCharts.value = true
    try {
      const clusterId = selectedClusterId.value

      // 并行加载所有API的数据
      const [fileClassificationResult, coldnessResult, formatCompressionResult, topTablesResult, coldestDataResult, summaryResult, recentTasksResult, fileDistributionResult, trendsResult] = await Promise.all([
        dashboardApi.getFileClassification(clusterId || undefined),
        dashboardApi.getEnhancedColdnessDistribution(clusterId || undefined),
        dashboardApi.getFormatCompressionDistribution(clusterId || undefined),
        dashboardApi.getTopTables(clusterId || undefined, 10),
        dashboardApi.getColdestData(10),
        dashboardApi.getSummary(clusterId || undefined),
        dashboardApi.getRecentTasks(5),
        dashboardApi.getFileDistribution(clusterId || undefined),
        dashboardApi.getTrends(clusterId || undefined, 30)
      ])

      fileClassificationItems.value = fileClassificationResult
      coldnessDistribution.value = coldnessResult
      formatCompressionItems.value = formatCompressionResult
      topTables.value = topTablesResult
      coldestData.value = coldestDataResult
      dashboardSummary.value = summaryResult
      recentTasks.value = recentTasksResult
      fileDistribution.value = fileDistributionResult
      trendData.value = trendsResult

      console.log('图表数据加载完成:', {
        fileClassification: fileClassificationResult,
        coldness: coldnessResult,
        formatCompression: formatCompressionResult
      })

      console.log('🔍 Debug 格式压缩分布数据:', {
        apiResponse: formatCompressionResult,
        computedData: formatCompressionData.value,
        totalSize: formatCompressionResult?.reduce((sum, item) => sum + item.total_size_gb, 0)
      })

      // 添加更详细的PieChart props调试
      console.log('📊 PieChart组件Props:', {
        formatCompressionData: formatCompressionData.value,
        dataType: typeof formatCompressionData.value,
        isArray: Array.isArray(formatCompressionData.value),
        itemCount: formatCompressionData.value?.length,
        firstItem: formatCompressionData.value?.[0]
      })
    } catch (error) {
      console.error('加载图表数据失败:', error)
      ElMessage.error('加载图表数据失败')
    } finally {
      isLoadingCharts.value = false
    }
  }

  // 刷新图表数据
  const refreshChartData = async () => {
    await loadChartData()
    ElMessage.success('图表数据已刷新')
  }

  // 文件分类饼状图点击事件
  const onFileClassificationClick = (item: any) => {
    console.log('文件分类点击:', item)
    ElMessage.info(`点击了 ${item.name}：${item.value.toLocaleString()} 个文件`)
  }

  // 冷数据分布饼状图点击事件
  const onColdnessDistributionClick = (item: any) => {
    console.log('冷数据分布点击:', item)
    ElMessage.info(`点击了 ${item.name}：${item.value.toFixed(2)}GB`)
  }


  // 任务状态类型映射
  const getTaskStatusType = (status: string) => {
    const statusMap: Record<string, string> = {
      'running': 'primary',
      'completed': 'success',
      'failed': 'danger',
      'pending': 'warning',
      'cancelled': 'info'
    }
    return statusMap[status] || 'info'
  }

  // 绘制趋势图
  const drawTrendChart = () => {
    if (!trendChartRef.value || trendData.value.length === 0) return

    const canvas = trendChartRef.value
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    const padding = 20

    // 清除画布
    ctx.clearRect(0, 0, width, height)

    // 获取数据范围
    const maxRatio = Math.max(...trendData.value.map(d => d.ratio))
    const minRatio = Math.min(...trendData.value.map(d => d.ratio))
    const range = maxRatio - minRatio || 1

    // 绘制网格线
    ctx.strokeStyle = '#e5e7eb'
    ctx.lineWidth = 1
    for (let i = 1; i < 4; i++) {
      const y = padding + (height - 2 * padding) * i / 4
      ctx.beginPath()
      ctx.moveTo(padding, y)
      ctx.lineTo(width - padding, y)
      ctx.stroke()
    }

    // 绘制趋势线
    if (trendData.value.length > 1) {
      ctx.strokeStyle = '#3b82f6'
      ctx.lineWidth = 2
      ctx.beginPath()

      trendData.value.forEach((point, index) => {
        const x = padding + (width - 2 * padding) * index / (trendData.value.length - 1)
        const y = height - padding - (height - 2 * padding) * (point.ratio - minRatio) / range

        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()

      // 绘制数据点
      ctx.fillStyle = '#3b82f6'
      trendData.value.forEach((point, index) => {
        const x = padding + (width - 2 * padding) * index / (trendData.value.length - 1)
        const y = height - padding - (height - 2 * padding) * (point.ratio - minRatio) / range

        ctx.beginPath()
        ctx.arc(x, y, 3, 0, 2 * Math.PI)
        ctx.fill()
      })
    }
  }

  // 监听本页下拉和全局选择的集群变化
  watch(selectedClusterId, async (newClusterId) => {
    console.log('集群选择变化:', newClusterId)
    await loadChartData()
  })
  watch(
    () => monitoringStore.settings.selectedCluster,
    async (cid) => {
      selectedClusterId.value = cid
      await loadChartData()
    }
  )

  // 监听趋势数据变化并重绘图表
  watch(trendData, () => {
    drawTrendChart()
  }, { deep: true })

  // 生命周期
  onMounted(async () => {
    try {
      // 同步已选集群
      selectedClusterId.value = monitoringStore.settings.selectedCluster
      // 加载图表数据
      await loadChartData()
      await nextTick()
      drawTrendChart()
    } catch (e: any) {
      console.error('Dashboard mount error:', e)
      renderError.value = e?.message || String(e)
    }
  })
</script>

<style scoped>
  .dashboard {
    padding: var(--space-3);
    min-height: 100vh;
    background: var(--bg-app);
    max-width: 1600px;
    margin: 0 auto;
  }

  /* 顶部概览统计卡片样式 */
  .overview-stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .stat-card {
    background: var(--bg-primary);
    border: 1px solid var(--gray-150);
    border-radius: var(--radius-md);
    padding: var(--space-3);
    display: flex;
    align-items: center;
    gap: var(--space-3);
    box-shadow: var(--elevation-0);
    transition: all var(--transition-normal);
    min-height: 60px;
  }

  .stat-card:hover {
    box-shadow: var(--elevation-2);
    transform: translateY(-1px);
  }

  .stat-icon {
    width: 32px;
    height: 32px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--primary-50);
    color: var(--primary-500);
    font-size: 16px;
    flex-shrink: 0;
  }

  .stat-icon.small-files {
    background: var(--red-50);
    color: var(--red-500);
  }

  .stat-icon.storage {
    background: var(--yellow-50);
    color: var(--yellow-600);
  }

  .stat-icon.clusters {
    background: var(--green-50);
    color: var(--green-500);
  }

  .stat-content {
    flex: 1;
  }

  .stat-value {
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
    color: var(--gray-900);
    line-height: 1.2;
  }

  .stat-label {
    font-size: var(--text-xs);
    color: var(--gray-600);
    margin-top: 2px;
  }

  /* 双饼状图区域样式 */
  .pie-charts-section {
    background: var(--bg-secondary);
    padding: var(--space-4);
    border-radius: var(--radius-xl);
    border: 1px solid var(--gray-100);
    box-shadow: var(--elevation-1);
    margin-bottom: var(--space-4);
  }



  .triple-pie-charts {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: var(--space-4);
    min-height: 480px;
  }

  .chart-card {
    background: var(--bg-primary);
    border: 1px solid var(--gray-150);
    border-radius: var(--radius-xl);
    overflow: hidden;
    box-shadow: var(--elevation-1);
    transition: all var(--transition-normal);
  }

  .chart-card:hover {
    box-shadow: var(--elevation-3);
    transform: translateY(-1px);
  }

  .chart-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4);
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--gray-200);
  }

  .chart-header h3 {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
    color: var(--gray-900);
    margin: 0;
  }

  .chart-header .el-icon {
    color: var(--primary-500);
    font-size: var(--text-lg);
  }

  .chart-content {
    padding: var(--space-4) var(--space-3) var(--space-4);
    background: var(--bg-primary);
  }


  .section-title {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    font-size: var(--text-2xl);
    font-weight: var(--font-semibold);
    color: var(--gray-900);
    margin: 0;
  }

  .section-title .el-icon {
    color: var(--primary-500);
    font-size: var(--text-xl);
  }

  /* 排行榜区域样式 */
  .rankings-section {
    background: var(--bg-secondary);
    padding: var(--space-4);
    border-radius: var(--radius-xl);
    border: 1px solid var(--gray-100);
    box-shadow: var(--elevation-1);
  }



  .dual-rankings {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-5);
    min-height: 500px;
    width: 100%;
  }

  .ranking-card {
    background: var(--bg-primary);
    border: 1px solid var(--gray-150);
    border-radius: var(--radius-xl);
    overflow: hidden;
    box-shadow: var(--elevation-1);
    transition: all var(--transition-normal);
  }

  .ranking-card:hover {
    box-shadow: var(--elevation-3);
    transform: translateY(-1px);
  }

  .ranking-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4);
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--gray-200);
  }

  .ranking-header h3 {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
    color: var(--gray-900);
    margin: 0;
  }

  .ranking-header .el-icon {
    color: var(--primary-500);
    font-size: var(--text-lg);
  }

  .ranking-content {
    padding: var(--space-4);
    background: var(--bg-primary);
    max-height: 450px;
    overflow-y: auto;
  }


  /* 响应式适配 */
  @media (max-width: 1200px) {
    .quad-pie-charts {
      grid-template-columns: 1fr 1fr;
      gap: var(--space-4);
    }

    .triple-pie-charts {
      grid-template-columns: 1fr 1fr;
      gap: var(--space-4);
      min-height: 400px;
    }

    .dual-rankings {
      grid-template-columns: 1fr;
      gap: var(--space-4);
    }

    .overview-stats {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 900px) {
    .quad-pie-charts {
      grid-template-columns: 1fr;
      gap: var(--space-4);
    }

    .triple-pie-charts {
      grid-template-columns: 1fr;
      gap: var(--space-4);
      min-height: 360px;
    }
  }

  @media (max-width: 768px) {
    .dashboard {
      padding: var(--space-4);
    }

    .pie-charts-section,
    .rankings-section {
      padding: var(--space-3);
    }

    .overview-stats {
      grid-template-columns: 1fr;
      gap: var(--space-3);
    }

    .charts-header {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-4);
    }

    .header-actions {
      width: 100%;
      justify-content: flex-end;
    }

    .chart-card {
      min-height: 450px;
    }
  }
</style>
