<template>
  <el-card
    class="file-card"
    shadow="hover"
  >
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon
            class="header-icon"
            :size="20"
          >
            <Document />
          </el-icon>
          <span class="header-title">文件统计</span>
        </div>
        <div class="header-right">
          <el-tag
            :type="statusType"
            size="small"
            effect="dark"
          >
            {{ fileStatus }}
          </el-tag>
        </div>
      </div>
    </template>

    <div class="card-content">
      <div class="file-overview">
        <div class="overview-chart">
          <div class="chart-container">
            <div
              class="donut-chart"
              :style="donutStyle"
            >
              <div class="chart-center">
                <div class="center-value">{{ totalFiles }}</div>
                <div class="center-label">总文件数</div>
              </div>
            </div>
          </div>
        </div>

        <div class="overview-stats">
          <div class="stat-item">
            <div class="stat-icon total">
              <el-icon :size="16"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ formatNumber(summary.total_files) }}</div>
              <div class="stat-label">总文件数</div>
            </div>
          </div>

          <div class="stat-item">
            <div class="stat-icon normal">
              <el-icon :size="16"><DocumentChecked /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ formatNumber(normalFiles) }}</div>
              <div class="stat-label">正常文件</div>
            </div>
          </div>

          <div class="stat-item">
            <div class="stat-icon size">
              <el-icon :size="16"><Coin /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ totalSizeFormatted }}</div>
              <div class="stat-label">总大小</div>
            </div>
          </div>
        </div>
      </div>

      <div
        class="file-metrics"
        v-if="showMetrics"
      >
        <div class="metric-row">
          <div class="metric-item">
            <span class="metric-label">平均文件大小</span>
            <span class="metric-value">{{ avgFileSize }}</span>
          </div>
        </div>

        <div class="metric-row">
          <div class="metric-item">
            <span class="metric-label">文件密度</span>
            <span class="metric-value">{{ fileDensity }}</span>
          </div>
        </div>

        <div class="metric-row">
          <div class="metric-item">
            <span class="metric-label">存储效率</span>
            <div class="efficiency-indicator">
              <el-progress
                :percentage="storageEfficiency"
                :color="efficiencyColor"
                :show-text="false"
                stroke-width="4"
                style="width: 60px"
              />
              <span class="efficiency-text">{{ storageEfficiency }}%</span>
            </div>
          </div>
        </div>
      </div>

      <div
        class="trend-indicator"
        v-if="showTrend"
      >
        <div class="trend-header">
          <span class="trend-title">文件趋势</span>
          <div class="trend-period">
            <el-radio-group
              v-model="trendPeriod"
              size="small"
            >
              <el-radio-button value="7d">7天</el-radio-button>
              <el-radio-button value="30d">30天</el-radio-button>
            </el-radio-group>
          </div>
        </div>

        <div class="mini-trend-chart">
          <div
            class="trend-line"
            :style="trendLineStyle"
          ></div>
          <div
            class="trend-change"
            :class="trendChangeClass"
          >
            <el-icon :size="12">
              <component :is="trendIcon" />
            </el-icon>
            <span>{{ trendChangeText }}</span>
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import {
    Document,
    DocumentChecked,
    Coin,
    ArrowUp,
    CaretBottom,
    Minus
  } from '@element-plus/icons-vue'
  import { useDashboardStore } from '@/stores/dashboard'
  import { useMonitoringStore } from '@/stores/monitoring'

  interface Props {
    showMetrics?: boolean
    showTrend?: boolean
  }

  const props = withDefaults(defineProps<Props>(), {
    showMetrics: true,
    showTrend: true
  })

  const dashboardStore = useDashboardStore()
  const monitoringStore = useMonitoringStore()

  const trendPeriod = ref<'7d' | '30d'>('7d')

  // 计算属性
  const summary = computed(() => dashboardStore.summary)
  const totalFiles = computed(() => formatNumber(summary.value.total_files))
  const normalFiles = computed(() => summary.value.total_files - summary.value.total_small_files)

  const totalSizeFormatted = computed(() => {
    const sizeGB = summary.value.total_size_gb
    if (sizeGB >= 1000) {
      return `${(sizeGB / 1000).toFixed(1)} TB`
    } else if (sizeGB >= 1) {
      return `${sizeGB.toFixed(1)} GB`
    } else {
      return `${(sizeGB * 1024).toFixed(0)} MB`
    }
  })

  const fileStatus = computed(() => {
    const ratio = (summary.value.total_small_files / summary.value.total_files) * 100
    if (ratio < 20) return '优秀'
    if (ratio < 40) return '良好'
    if (ratio < 60) return '一般'
    return '需优化'
  })

  const statusType = computed(() => {
    const ratio = (summary.value.total_small_files / summary.value.total_files) * 100
    if (ratio < 20) return 'success'
    if (ratio < 40) return 'info'
    if (ratio < 60) return 'warning'
    return 'danger'
  })

  const avgFileSize = computed(() => {
    if (summary.value.total_files === 0) return '--'
    const avgSizeMB = (summary.value.total_size_gb * 1024) / summary.value.total_files
    if (avgSizeMB >= 1024) {
      return `${(avgSizeMB / 1024).toFixed(1)} GB`
    } else {
      return `${avgSizeMB.toFixed(1)} MB`
    }
  })

  const fileDensity = computed(() => {
    if (summary.value.total_tables === 0) return '--'
    const density = summary.value.total_files / summary.value.total_tables
    return `${density.toFixed(0)} 文件/表`
  })

  const storageEfficiency = computed(() => {
    const ratio = (summary.value.total_small_files / summary.value.total_files) * 100
    return Math.max(0, 100 - Math.round(ratio))
  })

  const efficiencyColor = computed(() => {
    const efficiency = storageEfficiency.value
    if (efficiency >= 80) return '#67C23A'
    if (efficiency >= 60) return '#E6A23C'
    return '#F56C6C'
  })

  const donutStyle = computed(() => {
    const smallFileRatio = (summary.value.total_small_files / summary.value.total_files) * 100 || 0
    const normalRatio = 100 - smallFileRatio

    return {
      background: `conic-gradient(
      #67C23A 0deg ${normalRatio * 3.6}deg,
      #F56C6C ${normalRatio * 3.6}deg 360deg
    )`
    }
  })

  // 模拟趋势数据
  const trendChangeText = computed(() => '+12.5%')
  const trendChangeClass = computed(() => 'positive')
  const trendIcon = computed(() => ArrowUp)
  const trendLineStyle = computed(() => ({
    background: 'linear-gradient(90deg, #409EFF 0%, #67C23A 100%)',
    height: '3px',
    borderRadius: '2px'
  }))

  // 方法
  function formatNumber(num: number): string {
    return monitoringStore.formatNumber(num)
  }
</script>

<style scoped>
  .file-card {
    border-radius: 12px;
    transition: all 0.3s ease;
    background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
    color: white;
  }

  .file-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(116, 185, 255, 0.25);
  }

  .file-card :deep(.el-card__header) {
    background: rgba(255, 255, 255, 0.1);
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .header-icon {
    color: rgba(255, 255, 255, 0.9);
  }

  .header-title {
    font-weight: 600;
    color: white;
    font-size: 16px;
  }

  .file-overview {
    display: grid;
    grid-template-columns: 120px 1fr;
    gap: 20px;
    margin-bottom: 20px;
  }

  .overview-chart {
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .donut-chart {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }

  .donut-chart::before {
    content: '';
    position: absolute;
    width: 50px;
    height: 50px;
    background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
    border-radius: 50%;
    z-index: 1;
  }

  .chart-center {
    position: relative;
    z-index: 2;
    text-align: center;
  }

  .center-value {
    font-size: 14px;
    font-weight: bold;
    color: white;
    line-height: 1;
  }

  .center-label {
    font-size: 8px;
    color: rgba(255, 255, 255, 0.8);
    margin-top: 2px;
  }

  .overview-stats {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .stat-item {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .stat-icon {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .stat-icon.total {
    background: rgba(64, 158, 255, 0.3);
  }

  .stat-icon.normal {
    background: rgba(103, 194, 58, 0.3);
  }

  .stat-icon.size {
    background: rgba(230, 162, 60, 0.3);
  }

  .stat-info {
    flex: 1;
  }

  .stat-value {
    font-size: 16px;
    font-weight: bold;
    color: white;
    line-height: 1.2;
  }

  .stat-label {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.8);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .file-metrics {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 20px;
  }

  .metric-row {
    display: flex;
    align-items: center;
    padding: 8px 0;
  }

  .metric-row:not(:last-child) {
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }

  .metric-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }

  .metric-label {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.8);
  }

  .metric-value {
    font-size: 13px;
    font-weight: 500;
    color: white;
  }

  .efficiency-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .efficiency-text {
    font-size: 12px;
    font-weight: bold;
    color: white;
  }

  .trend-indicator {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 16px;
  }

  .trend-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .trend-title {
    font-size: 14px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
  }

  .trend-period :deep(.el-radio-button__inner) {
    background: transparent;
    border-color: rgba(255, 255, 255, 0.3);
    color: rgba(255, 255, 255, 0.8);
    font-size: 11px;
    padding: 4px 8px;
  }

  .trend-period :deep(.el-radio-button__inner:hover) {
    color: white;
    border-color: rgba(255, 255, 255, 0.5);
  }

  .trend-period :deep(.el-radio-button.is-active .el-radio-button__inner) {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.5);
    color: white;
  }

  .mini-trend-chart {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .trend-line {
    width: 100%;
    height: 3px;
    border-radius: 2px;
  }

  .trend-change {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 500;
  }

  .trend-change.positive {
    color: #67c23a;
  }

  .trend-change.negative {
    color: #f56c6c;
  }

  @media (max-width: 768px) {
    .file-overview {
      grid-template-columns: 1fr;
      gap: 16px;
    }

    .overview-chart {
      justify-content: flex-start;
    }

    .overview-stats {
      gap: 10px;
    }

    .stat-item {
      gap: 10px;
    }

    .trend-header {
      flex-direction: column;
      gap: 8px;
      align-items: flex-start;
    }
  }
</style>
