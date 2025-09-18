<template>
  <div class="table-file-count-chart">
    <div class="chart-header">
      <div class="header-left">
        <h3 class="chart-title">表文件数监控</h3>
        <p class="chart-subtitle">实时监控所有表的文件数量及变化趋势</p>
      </div>
      <div class="header-right">
        <el-select
          v-model="selectedView"
          size="small"
          style="width: 120px; margin-right: 12px"
          @change="handleViewChange"
        >
          <el-option
            label="图表视图"
            value="chart"
          />
          <el-option
            label="表格视图"
            value="table"
          />
        </el-select>

        <el-button-group size="small">
          <el-button
            @click="handleRefresh"
            :loading="loading"
            :icon="Refresh"
          >
            刷新
          </el-button>
          <el-button
            @click="handleExport"
            :icon="Download"
          >
            导出
          </el-button>
        </el-button-group>
      </div>
    </div>

    <div class="chart-container">
      <!-- 图表视图 -->
      <div
        v-if="selectedView === 'chart'"
        class="chart-view"
      >
        <div
          v-if="loading"
          class="chart-loading"
        >
          <el-skeleton animated>
            <template #template>
              <el-skeleton-item
                variant="rect"
                style="width: 100%; height: 400px"
              />
            </template>
          </el-skeleton>
        </div>

        <div
          v-else-if="error"
          class="chart-error"
        >
          <el-empty description="数据加载失败">
            <el-button
              type="primary"
              @click="handleRefresh"
              >重新加载</el-button
            >
          </el-empty>
        </div>

        <v-chart
          v-else
          class="file-count-echarts"
          :option="chartOption"
          :loading="loading"
          autoresize
          @click="handleChartClick"
          style="height: 400px"
        />
      </div>

      <!-- 表格视图 -->
      <div
        v-else
        class="table-view"
      >
        <el-table
          :data="tableData"
          stripe
          :loading="loading"
          empty-text="暂无数据"
          @row-click="handleTableRowClick"
          max-height="500px"
        >
          <el-table-column
            type="index"
            label="排名"
            width="60"
          />

          <el-table-column
            prop="cluster_name"
            label="集群"
            width="100"
            show-overflow-tooltip
          />

          <el-table-column
            label="表名"
            min-width="200"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              <div class="table-info">
                <div
                  class="table-name clickable"
                  @click="navigateToTableDetail(row)"
                >
                  {{ row.database_name }}.{{ row.table_name }}
                </div>
                <div class="table-meta">
                  <span class="cluster-name">{{ row.cluster_name }}</span>
                  <el-tag
                    v-if="row.table_type"
                    size="small"
                    :type="getTableTypeColor(row.table_type)"
                    style="margin-left: 8px"
                  >
                    {{ formatTableType(row.table_type) }}
                  </el-tag>
                  <el-tag
                    v-if="row.storage_format"
                    size="small"
                    type="info"
                    style="margin-left: 4px"
                  >
                    {{ row.storage_format }}
                  </el-tag>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column
            prop="current_files"
            label="当前文件数"
            width="120"
            sortable
          >
            <template #default="{ row }">
              <span class="file-count">{{ formatNumber(row.current_files) }}</span>
            </template>
          </el-table-column>

          <el-table-column
            prop="total_size"
            label="表总大小"
            width="120"
            sortable
          >
            <template #default="{ row }">
              <span class="size-value">{{ formatSize(row.total_size || 0) }}</span>
            </template>
          </el-table-column>

          <el-table-column
            prop="small_file_ratio"
            label="小文件占比"
            width="120"
            sortable
          >
            <template #default="{ row }">
              <div class="ratio-indicator">
                <span :class="getRatioClass(row.small_file_ratio || 0)">
                  {{ (row.small_file_ratio || 0).toFixed(1) }}%
                </span>
                <div class="ratio-bar">
                  <div
                    class="ratio-fill"
                    :style="{ width: Math.min(row.small_file_ratio || 0, 100) + '%' }"
                    :class="getRatioClass(row.small_file_ratio || 0)"
                  ></div>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column
            prop="avg_file_size"
            label="平均文件大小"
            width="130"
            sortable
          >
            <template #default="{ row }">
              <span class="size-value">{{ formatSize(row.avg_file_size || 0) }}</span>
            </template>
          </el-table-column>

          <el-table-column
            label="分区信息"
            width="120"
            sortable="custom"
            :sort-by="'is_partitioned'"
          >
            <template #default="{ row }">
              <div class="partition-info">
                <el-tag
                  v-if="row.is_partitioned"
                  size="small"
                  type="warning"
                >
                  {{ row.partition_count }}个分区
                </el-tag>
                <el-tag
                  v-else
                  size="small"
                  type=""
                >
                  未分区
                </el-tag>
              </div>
            </template>
          </el-table-column>

          <el-table-column
            label="7天变化"
            width="100"
          >
            <template #default="{ row }">
              <div class="trend-indicator">
                <el-icon
                  v-if="row.trend_7d > 0"
                  style="color: #f56c6c"
                  ><ArrowUp
                /></el-icon>
                <el-icon
                  v-else-if="row.trend_7d < 0"
                  style="color: #67c23a"
                  ><CaretBottom
                /></el-icon>
                <el-icon
                  v-else
                  style="color: #909399"
                  ><Minus
                /></el-icon>
                <span :class="getTrendClass(row.trend_7d)"
                  >{{ Math.abs(row.trend_7d).toFixed(1) }}%</span
                >
              </div>
            </template>
          </el-table-column>

          <el-table-column
            label="30天变化"
            width="100"
          >
            <template #default="{ row }">
              <div class="trend-indicator">
                <el-icon
                  v-if="row.trend_30d > 0"
                  style="color: #f56c6c"
                  ><ArrowUp
                /></el-icon>
                <el-icon
                  v-else-if="row.trend_30d < 0"
                  style="color: #67c23a"
                  ><CaretBottom
                /></el-icon>
                <el-icon
                  v-else
                  style="color: #909399"
                  ><Minus
                /></el-icon>
                <span :class="getTrendClass(row.trend_30d)"
                  >{{ Math.abs(row.trend_30d).toFixed(1) }}%</span
                >
              </div>
            </template>
          </el-table-column>

          <el-table-column
            prop="last_scan"
            label="最后扫描"
            width="140"
          >
            <template #default="{ row }">
              <span class="time-value">{{ formatTime(row.last_scan) }}</span>
            </template>
          </el-table-column>

          <el-table-column
            label="操作"
            width="120"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                type="text"
                size="small"
                @click.stop="handleViewTrend(row)"
              >
                查看趋势
              </el-button>
              <el-button
                type="text"
                size="small"
                @click.stop="handleAnalyze(row)"
              >
                分析
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 表趋势弹窗 -->
    <el-dialog
      v-model="trendDialogVisible"
      :title="`${selectedTable?.database_name}.${selectedTable?.table_name} - 文件数趋势`"
      width="80%"
      top="5vh"
    >
      <div class="trend-dialog-content">
        <div class="trend-controls">
          <el-radio-group
            v-model="trendPeriod"
            size="small"
            @change="loadTableTrend"
          >
            <el-radio-button value="7">7天</el-radio-button>
            <el-radio-button value="30">30天</el-radio-button>
            <el-radio-button value="90">90天</el-radio-button>
          </el-radio-group>
        </div>

        <div class="trend-chart-container">
          <v-chart
            v-if="tableTrendData.length > 0"
            class="trend-chart"
            :option="trendChartOption"
            :loading="trendLoading"
            autoresize
            style="height: 350px"
          />
          <el-empty
            v-else
            description="暂无趋势数据"
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, watch, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { use } from 'echarts/core'
  import { CanvasRenderer } from 'echarts/renderers'
  import { LineChart, BarChart } from 'echarts/charts'
  import {
    GridComponent,
    TooltipComponent,
    LegendComponent,
    TitleComponent,
    DataZoomComponent,
    ToolboxComponent
  } from 'echarts/components'
  import VChart from 'vue-echarts'
  import { Refresh, Download, ArrowUp, CaretBottom, Minus } from '@element-plus/icons-vue'
  import { ElMessage } from 'element-plus'
  import { dashboardApi, type TableFileCountItem, type TableFileCountPoint } from '@/api/dashboard'
  import { useMonitoringStore } from '@/stores/monitoring'
  import dayjs from 'dayjs'

  use([
    CanvasRenderer,
    LineChart,
    BarChart,
    GridComponent,
    TooltipComponent,
    LegendComponent,
    TitleComponent,
    DataZoomComponent,
    ToolboxComponent
  ])

  interface Props {
    clusterId?: number
    limit?: number
    refreshing?: boolean
  }

  const props = withDefaults(defineProps<Props>(), {
    limit: 20,
    refreshing: false
  })

  const emit = defineEmits<{
    'table-select': [tableId: string]
    'table-analyze': [table: TableFileCountItem]
    refresh: []
  }>()

  const monitoringStore = useMonitoringStore()
  const router = useRouter()

  // 数据状态
  const loading = ref(false)
  const error = ref<string | null>(null)
  const tableData = ref<TableFileCountItem[]>([])

  // 视图状态
  const selectedView = ref<'chart' | 'table'>('table')

  // 趋势弹窗状态
  const trendDialogVisible = ref(false)
  const selectedTable = ref<TableFileCountItem | null>(null)
  const tableTrendData = ref<TableFileCountPoint[]>([])
  const trendLoading = ref(false)
  const trendPeriod = ref<string>('30')

  // 计算属性
  const chartOption = computed(() => {
    if (!tableData.value || tableData.value.length === 0) {
      return {
        title: {
          text: '暂无数据',
          left: 'center',
          top: 'center',
          textStyle: {
            fontSize: 14,
            color: '#999'
          }
        }
      }
    }

    const data = tableData.value.slice(0, 15) // 只显示前15个表

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        formatter: function (params: any) {
          const item = params[0]
          const table = data[item.dataIndex]
          return `
          <div style="margin: 0; padding: 8px;">
            <div style="font-weight: 600; margin-bottom: 6px;">
              ${table.database_name}.${table.table_name}
            </div>
            <div style="color: #666; font-size: 12px; margin-bottom: 8px;">
              集群: ${table.cluster_name}
            </div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
              <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${item.color}"></span>
              <span>文件数: ${formatNumber(item.value)}</span>
            </div>
            <div style="font-size: 12px; color: #666; margin-bottom: 4px;">
              表总大小: ${formatSize(table.total_size || 0)}
            </div>
            <div style="font-size: 12px; color: #666; margin-bottom: 4px;">
              小文件占比: ${(table.small_file_ratio || 0).toFixed(1)}%
            </div>
            <div style="font-size: 12px; color: #666; margin-bottom: 6px;">
              平均文件大小: ${formatSize(table.avg_file_size || 0)}
            </div>
            <div style="margin-top: 4px; font-size: 12px; color: #999;">
              7天变化: ${table.trend_7d > 0 ? '+' : ''}${table.trend_7d.toFixed(1)}% | 
              30天变化: ${table.trend_30d > 0 ? '+' : ''}${table.trend_30d.toFixed(1)}%
            </div>
          </div>
        `
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: data.map(item => `${item.database_name}.${item.table_name}`),
        axisLabel: {
          rotate: 45,
          interval: 0,
          fontSize: 10,
          color: '#666',
          formatter: function (value: string) {
            return value.length > 20 ? value.substring(0, 20) + '...' : value
          }
        },
        axisTick: {
          alignWithLabel: true
        }
      },
      yAxis: {
        type: 'value',
        name: '文件数',
        nameTextStyle: {
          color: '#666'
        },
        axisLabel: {
          formatter: function (value: number) {
            return formatNumber(value)
          }
        }
      },
      series: [
        {
          name: '文件数',
          type: 'bar',
          data: data.map(item => item.current_files),
          itemStyle: {
            color: function (params: any) {
              const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399']
              return colors[params.dataIndex % colors.length]
            },
            borderRadius: [4, 4, 0, 0]
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowOffsetY: 0,
              shadowColor: 'rgba(0, 0, 0, 0.3)'
            }
          }
        }
      ]
    }
  })

  const trendChartOption = computed(() => {
    if (!tableTrendData.value || tableTrendData.value.length === 0) {
      return {}
    }

    const data = tableTrendData.value

    return {
      tooltip: {
        trigger: 'axis',
        formatter: function (params: any) {
          const point = params[0]
          const item = data[point.dataIndex]
          return `
          <div style="margin: 0; padding: 8px;">
            <div style="font-weight: 600; margin-bottom: 6px;">
              ${dayjs(item.date).format('YYYY-MM-DD HH:mm')}
            </div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
              <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #409EFF"></span>
              <span>总文件数: ${formatNumber(item.total_files)}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
              <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #F56C6C"></span>
              <span>小文件数: ${formatNumber(item.small_files)}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #E6A23C"></span>
              <span>小文件占比: ${item.ratio.toFixed(1)}%</span>
            </div>
          </div>
        `
        }
      },
      legend: {
        top: 10,
        data: ['总文件数', '小文件数', '小文件占比']
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: data.map(item => dayjs(item.date).format('MM-DD HH:mm')),
        axisLabel: {
          rotate: 45,
          color: '#666'
        }
      },
      yAxis: [
        {
          type: 'value',
          name: '文件数',
          position: 'left',
          axisLabel: {
            formatter: function (value: number) {
              return formatNumber(value)
            }
          }
        },
        {
          type: 'value',
          name: '占比(%)',
          position: 'right',
          min: 0,
          max: 100,
          axisLabel: {
            formatter: '{value}%'
          }
        }
      ],
      series: [
        {
          name: '总文件数',
          type: 'line',
          data: data.map(item => item.total_files),
          smooth: true,
          itemStyle: { color: '#409EFF' },
          lineStyle: { color: '#409EFF' }
        },
        {
          name: '小文件数',
          type: 'line',
          data: data.map(item => item.small_files),
          smooth: true,
          itemStyle: { color: '#F56C6C' },
          lineStyle: { color: '#F56C6C' }
        },
        {
          name: '小文件占比',
          type: 'line',
          yAxisIndex: 1,
          data: data.map(item => item.ratio),
          smooth: true,
          itemStyle: { color: '#E6A23C' },
          lineStyle: { color: '#E6A23C', type: 'dashed' }
        }
      ]
    }
  })

  // 方法
  async function loadData() {
    loading.value = true
    error.value = null

    try {
      const data = await dashboardApi.getTableFileCounts(props.clusterId, props.limit)

      // 添加模拟的大小和占比数据（实际应用中应该从API返回）
      const enhancedData = data.map((item, index) => ({
        ...item,
        total_size: generateMockSize(item.current_files || 0),
        small_file_ratio: generateMockRatio(),
        avg_file_size: generateMockAvgSize(item.current_files || 0)
      }))

      tableData.value = enhancedData
    } catch (err) {
      error.value = '数据加载失败'
      console.error('Failed to load table file counts:', err)
    } finally {
      loading.value = false
    }
  }

  // 模拟数据生成函数（实际应用中应删除）
  function generateMockSize(fileCount: number): number {
    // 基于文件数量生成合理的总大小
    const baseSize = fileCount * (Math.random() * 50 + 10) * 1024 * 1024 // 10-60MB per file average
    return Math.floor(baseSize * (0.5 + Math.random())) // 添加一些随机性
  }

  function generateMockRatio(): number {
    // 生成0-95%的小文件占比，偏向较高值
    const ratios = [15, 25, 35, 45, 55, 65, 75, 85, 90]
    return ratios[Math.floor(Math.random() * ratios.length)]
  }

  function generateMockAvgSize(fileCount: number): number {
    // 根据小文件占比生成平均文件大小
    const baseAvg = Math.random() * 30 + 5 // 5-35MB base
    return baseAvg * 1024 * 1024 // Convert to bytes
  }

  async function loadTableTrend() {
    if (!selectedTable.value) return

    trendLoading.value = true

    try {
      const data = await dashboardApi.getTableFileTrends(
        selectedTable.value.table_id,
        parseInt(trendPeriod.value)
      )
      tableTrendData.value = data
    } catch (err) {
      ElMessage.error('趋势数据加载失败')
      console.error('Failed to load table trends:', err)
    } finally {
      trendLoading.value = false
    }
  }

  function handleRefresh() {
    emit('refresh')
    loadData()
  }

  function handleExport() {
    ElMessage.info('导出功能开发中...')
  }

  function handleViewChange() {
    // 视图切换时的处理
  }

  function handleChartClick(params: any) {
    const table = tableData.value[params.dataIndex]
    if (table) {
      handleViewTrend(table)
    }
  }

  function handleTableRowClick(row: TableFileCountItem) {
    router.push(`/tables/${row.cluster_id || 1}/${row.database_name}/${row.table_name}`)
  }

  function handleViewTrend(table: TableFileCountItem) {
    selectedTable.value = table
    trendDialogVisible.value = true
    loadTableTrend()
  }

  function handleAnalyze(table: TableFileCountItem) {
    emit('table-analyze', table)
  }

  function formatNumber(num: number): string {
    return monitoringStore.formatNumber(num)
  }

  function formatTime(time: string): string {
    return dayjs(time).format('MM-DD HH:mm')
  }

  function getTrendClass(trend: number): string {
    if (trend > 0) return 'trend-up'
    if (trend < 0) return 'trend-down'
    return 'trend-stable'
  }

  function formatSize(bytes: number): string {
    if (bytes === 0) return '0 B'

    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  function getRatioClass(ratio: number): string {
    if (ratio >= 80) return 'ratio-high'
    if (ratio >= 50) return 'ratio-medium'
    if (ratio >= 20) return 'ratio-low'
    return 'ratio-minimal'
  }

  function getTableTypeColor(tableType: string): string {
    switch (tableType) {
      case 'MANAGED_TABLE':
        return 'success'
      case 'EXTERNAL_TABLE':
        return 'warning'
      case 'VIEW':
        return 'info'
      default:
        return ''
    }
  }

  function formatTableType(tableType: string): string {
    switch (tableType) {
      case 'MANAGED_TABLE':
        return '托管表'
      case 'EXTERNAL_TABLE':
        return '外部表'
      case 'VIEW':
        return '视图'
      default:
        return tableType || '未知'
    }
  }

  function navigateToTableDetail(row: any): void {
    router.push(`/tables/${props.clusterId}/${row.database_name}/${row.table_name}`)
  }

  // 监听
  watch(
    () => props.clusterId,
    () => {
      loadData()
    }
  )

  watch(
    () => props.refreshing,
    newVal => {
      if (newVal) {
        loadData()
      }
    }
  )

  // 生命周期
  onMounted(() => {
    loadData()
  })
</script>

<style scoped>
  .table-file-count-chart {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    overflow: hidden;
  }

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 20px 24px 16px;
    border-bottom: 1px solid #f0f0f0;
  }

  .header-left {
    flex: 1;
  }

  .chart-title {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
    line-height: 1.4;
  }

  .chart-subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    color: #6b7280;
    line-height: 1.4;
  }

  .header-right {
    display: flex;
    align-items: center;
  }

  .chart-container {
    padding: 16px 24px;
  }

  .chart-loading,
  .chart-error {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 400px;
  }

  .file-count-echarts {
    width: 100%;
  }

  .table-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .table-name {
    font-weight: 600;
    color: #1f2937;
  }

  .table-name.clickable {
    cursor: pointer;
    transition: color 0.2s;
  }

  .table-name.clickable:hover {
    color: #409eff;
    text-decoration: underline;
  }

  .table-meta {
    font-size: 12px;
    color: #6b7280;
  }

  .file-count {
    font-weight: 600;
    color: #1f2937;
  }

  .trend-indicator {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .trend-up {
    color: #f56c6c;
  }

  .trend-down {
    color: #67c23a;
  }

  .trend-stable {
    color: #909399;
  }

  .time-value {
    font-size: 12px;
    color: #6b7280;
  }

  .size-value {
    font-weight: 600;
    color: #1f2937;
    font-size: 13px;
  }

  .ratio-indicator {
    display: flex;
    flex-direction: column;
    gap: 4px;
    align-items: center;
  }

  .ratio-indicator span {
    font-size: 13px;
    font-weight: 600;
  }

  .ratio-bar {
    width: 60px;
    height: 6px;
    background: #f1f5f9;
    border-radius: 3px;
    overflow: hidden;
  }

  .ratio-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s ease;
  }

  /* 小文件占比颜色分级 */
  .ratio-minimal {
    color: #059669;
  }

  .ratio-minimal.ratio-fill {
    background: linear-gradient(90deg, #059669, #10b981);
  }

  .ratio-low {
    color: #d97706;
  }

  .ratio-low.ratio-fill {
    background: linear-gradient(90deg, #d97706, #f59e0b);
  }

  .ratio-medium {
    color: #ea580c;
  }

  .ratio-medium.ratio-fill {
    background: linear-gradient(90deg, #ea580c, #f97316);
  }

  .ratio-high {
    color: #dc2626;
  }

  .ratio-high.ratio-fill {
    background: linear-gradient(90deg, #dc2626, #ef4444);
  }

  .trend-dialog-content {
    padding: 0;
  }

  .trend-controls {
    display: flex;
    justify-content: center;
    margin-bottom: 20px;
  }

  .trend-chart-container {
    min-height: 350px;
  }

  .trend-chart {
    width: 100%;
  }

  /* 响应式设计 */
  @media (max-width: 768px) {
    .chart-header {
      flex-direction: column;
      gap: 16px;
      align-items: flex-start;
    }

    .header-right {
      width: 100%;
      justify-content: flex-start;
    }

    .chart-container {
      padding: 12px 16px;
    }

    .chart-title {
      font-size: 16px;
    }

    .chart-subtitle {
      font-size: 13px;
    }
  }
</style>
