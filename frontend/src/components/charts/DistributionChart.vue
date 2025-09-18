<template>
  <div class="distribution-chart">
    <div
      class="chart-header"
      v-if="showHeader"
    >
      <div class="header-left">
        <h3 class="chart-title">{{ title }}</h3>
        <p
          class="chart-subtitle"
          v-if="subtitle"
        >
          {{ subtitle }}
        </p>
      </div>
      <div class="header-right">
        <el-switch
          v-model="showPercentage"
          inline-prompt
          active-text="百分比"
          inactive-text="数值"
          size="small"
        />
      </div>
    </div>

    <div
      class="chart-container"
      :style="containerStyle"
    >
      <div
        v-if="loading"
        class="chart-loading"
      >
        <el-skeleton animated>
          <template #template>
            <el-skeleton-item
              variant="circle"
              style="width: 200px; height: 200px; margin: 0 auto"
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
            @click="$emit('refresh')"
            >重新加载</el-button
          >
        </el-empty>
      </div>

      <div
        v-else-if="!data || data.length === 0"
        class="chart-empty"
      >
        <el-empty description="暂无分布数据" />
      </div>

      <v-chart
        v-else
        class="distribution-echarts"
        :option="chartOption"
        :loading="loading"
        autoresize
        @click="handleChartClick"
      />
    </div>

    <div
      class="chart-summary"
      v-if="showSummary && data && data.length > 0"
    >
      <div class="summary-stats">
        <div
          class="stat-item"
          v-for="item in summaryStats"
          :key="item.label"
        >
          <div class="stat-label">{{ item.label }}</div>
          <div
            class="stat-value"
            :style="{ color: item.color }"
          >
            {{ item.value }}
          </div>
        </div>
      </div>
    </div>

    <div
      class="chart-footer"
      v-if="showFooter"
    >
      <div class="distribution-table">
        <div class="table-header">
          <span class="header-item">大小范围</span>
          <span class="header-item">文件数量</span>
          <span class="header-item">占比</span>
        </div>
        <div
          class="table-row"
          v-for="(item, index) in distributionData"
          :key="item.size_range"
          @click="handleRowClick(item, index)"
        >
          <span class="row-item range">
            <span
              class="range-color"
              :style="{ backgroundColor: getItemColor(index) }"
            ></span>
            {{ item.size_range }}
          </span>
          <span class="row-item count">{{ formatNumber(item.count) }}</span>
          <span class="row-item percentage">{{ getPercentage(item) }}%</span>
        </div>
      </div>

      <div class="chart-actions">
        <el-button-group size="small">
          <el-button
            @click="handleExport"
            :loading="exporting"
          >
            <el-icon><Download /></el-icon>
          </el-button>
          <el-button
            @click="$emit('refresh')"
            :loading="refreshing"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
        </el-button-group>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { use } from 'echarts/core'
  import { CanvasRenderer } from 'echarts/renderers'
  import { PieChart } from 'echarts/charts'
  import { TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
  import VChart from 'vue-echarts'
  import { Download, Refresh } from '@element-plus/icons-vue'
  import { useCharts } from '@/composables/useCharts'
  import { useMonitoringStore } from '@/stores/monitoring'
  import type { FileDistributionItem } from '@/api/dashboard'

  use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent, TitleComponent])

  interface Props {
    data: FileDistributionItem[]
    title?: string
    subtitle?: string
    height?: number
    showHeader?: boolean
    showFooter?: boolean
    showSummary?: boolean
    loading?: boolean
    error?: string | null
    refreshing?: boolean
    exporting?: boolean
    theme?: 'light' | 'dark'
  }

  const props = withDefaults(defineProps<Props>(), {
    title: '文件大小分布',
    subtitle: '按文件大小范围显示文件数量分布',
    height: 400,
    showHeader: true,
    showFooter: true,
    showSummary: true,
    loading: false,
    error: null,
    refreshing: false,
    exporting: false,
    theme: 'light'
  })

  const emit = defineEmits<{
    refresh: []
    export: []
    'chart-click': [params: any]
    'row-click': [item: FileDistributionItem, index: number]
  }>()

  const { getDistributionChartOption } = useCharts()
  const monitoringStore = useMonitoringStore()

  const showPercentage = ref(false)

  // 计算属性
  const containerStyle = computed(() => ({
    height: `${props.height}px`,
    position: 'relative'
  }))

  const distributionData = computed(() => props.data || [])

  const totalCount = computed(() => {
    return distributionData.value.reduce((sum, item) => sum + item.count, 0)
  })

  const chartOption = computed(() => {
    if (!distributionData.value || distributionData.value.length === 0) {
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

    return getDistributionChartOption(distributionData.value)
  })

  const summaryStats = computed(() => {
    if (!distributionData.value || distributionData.value.length === 0) return []

    const smallFileThreshold = 128 // MB
    const smallFiles = distributionData.value.filter(item => {
      const range = item.size_range.toLowerCase()
      return range.includes('mb') && parseFloat(range) < smallFileThreshold
    })

    const smallFileCount = smallFiles.reduce((sum, item) => sum + item.count, 0)
    const smallFileRatio =
      totalCount.value > 0 ? ((smallFileCount / totalCount.value) * 100).toFixed(1) : '0'

    return [
      {
        label: '总文件数',
        value: formatNumber(totalCount.value),
        color: '#409EFF'
      },
      {
        label: '小文件数',
        value: formatNumber(smallFileCount),
        color: '#F56C6C'
      },
      {
        label: '小文件占比',
        value: `${smallFileRatio}%`,
        color: '#E6A23C'
      }
    ]
  })

  // 方法
  function formatNumber(num: number): string {
    return monitoringStore.formatNumber(num)
  }

  function getItemColor(index: number): string {
    return monitoringStore.getChartColor(index)
  }

  function getPercentage(item: FileDistributionItem): string {
    if (totalCount.value === 0) return '0.0'
    return ((item.count / totalCount.value) * 100).toFixed(1)
  }

  function handleChartClick(params: any) {
    emit('chart-click', params)
  }

  function handleRowClick(item: FileDistributionItem, index: number) {
    emit('row-click', item, index)
  }

  function handleExport() {
    emit('export')
  }
</script>

<style scoped>
  .distribution-chart {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    overflow: hidden;
    transition: all 0.3s ease;
  }

  .distribution-chart:hover {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
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
    background: #fafafa;
  }

  .chart-loading,
  .chart-error,
  .chart-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    background: white;
    border-radius: 8px;
  }

  .distribution-echarts {
    width: 100%;
    height: 100%;
    background: white;
    border-radius: 8px;
  }

  .chart-summary {
    padding: 16px 24px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .summary-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 20px;
  }

  .stat-item {
    text-align: center;
  }

  .stat-label {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.8);
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .stat-value {
    font-size: 18px;
    font-weight: bold;
    color: white;
  }

  .chart-footer {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 20px 24px;
    background: #f9fafb;
    border-top: 1px solid #f0f0f0;
    gap: 24px;
  }

  .distribution-table {
    flex: 1;
    min-width: 0;
  }

  .table-header {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr;
    gap: 16px;
    padding: 8px 0;
    border-bottom: 2px solid #e5e7eb;
    margin-bottom: 8px;
  }

  .header-item {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .table-row {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr;
    gap: 16px;
    padding: 8px 0;
    border-bottom: 1px solid #f3f4f6;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .table-row:hover {
    background: #f9fafb;
    border-radius: 4px;
    padding-left: 8px;
    padding-right: 8px;
    margin-left: -8px;
    margin-right: -8px;
  }

  .table-row:last-child {
    border-bottom: none;
  }

  .row-item {
    display: flex;
    align-items: center;
    font-size: 14px;
  }

  .row-item.range {
    gap: 8px;
  }

  .range-color {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .row-item.count {
    color: #374151;
    font-weight: 500;
  }

  .row-item.percentage {
    color: #6b7280;
    font-weight: 600;
  }

  .chart-actions {
    display: flex;
    align-items: flex-start;
    flex-shrink: 0;
  }

  /* 暗色主题 */
  .distribution-chart[data-theme='dark'] {
    background: #1f2937;
    color: white;
  }

  .distribution-chart[data-theme='dark'] .chart-header {
    border-bottom-color: #374151;
  }

  .distribution-chart[data-theme='dark'] .chart-title {
    color: white;
  }

  .distribution-chart[data-theme='dark'] .chart-subtitle {
    color: #d1d5db;
  }

  .distribution-chart[data-theme='dark'] .chart-container {
    background: #111827;
  }

  .distribution-chart[data-theme='dark'] .distribution-echarts {
    background: #1f2937;
  }

  .distribution-chart[data-theme='dark'] .chart-footer {
    background: #111827;
    border-top-color: #374151;
  }

  .distribution-chart[data-theme='dark'] .table-header {
    border-bottom-color: #4b5563;
  }

  .distribution-chart[data-theme='dark'] .header-item {
    color: #d1d5db;
  }

  .distribution-chart[data-theme='dark'] .table-row {
    border-bottom-color: #374151;
  }

  .distribution-chart[data-theme='dark'] .table-row:hover {
    background: #374151;
  }

  .distribution-chart[data-theme='dark'] .row-item.count {
    color: #d1d5db;
  }

  .distribution-chart[data-theme='dark'] .row-item.percentage {
    color: #9ca3af;
  }

  /* 响应式设计 */
  @media (max-width: 768px) {
    .chart-header {
      flex-direction: column;
      gap: 16px;
      align-items: flex-start;
    }

    .chart-footer {
      flex-direction: column;
      gap: 20px;
      align-items: stretch;
    }

    .chart-actions {
      align-self: center;
    }

    .summary-stats {
      grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
      gap: 16px;
    }

    .table-header,
    .table-row {
      grid-template-columns: 1.5fr 1fr 0.8fr;
      gap: 12px;
    }

    .header-item,
    .row-item {
      font-size: 13px;
    }
  }

  @media (max-width: 480px) {
    .chart-header {
      padding: 16px 16px 12px;
    }

    .chart-container {
      padding: 12px 16px;
    }

    .chart-summary {
      padding: 12px 16px;
    }

    .chart-footer {
      padding: 16px;
    }

    .chart-title {
      font-size: 16px;
    }

    .chart-subtitle {
      font-size: 13px;
    }

    .stat-value {
      font-size: 16px;
    }
  }
</style>
