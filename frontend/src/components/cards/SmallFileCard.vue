<template>
  <el-card
    class="small-file-card"
    shadow="hover"
  >
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon
            class="header-icon"
            :size="20"
          >
            <WarningFilled />
          </el-icon>
          <span class="header-title">小文件问题</span>
        </div>
        <div class="header-right">
          <el-tag
            :type="alertType"
            size="small"
            effect="dark"
          >
            <el-icon :size="12">
              <component :is="alertIcon" />
            </el-icon>
            {{ alertLevel }}
          </el-tag>
        </div>
      </div>
    </template>

    <div class="card-content">
      <div class="problem-overview">
        <div class="severity-indicator">
          <div class="severity-chart">
            <div
              class="chart-ring"
              :style="ringStyle"
            >
              <div class="ring-center">
                <div class="center-ratio">{{ smallFileRatio }}%</div>
                <div class="center-label">小文件占比</div>
              </div>
            </div>
          </div>

          <div
            class="severity-level"
            :class="severityClass"
          >
            <div class="level-text">{{ severityText }}</div>
            <div class="level-desc">{{ severityDescription }}</div>
          </div>
        </div>

        <div class="problem-stats">
          <div class="stat-grid">
            <div class="stat-cell danger">
              <div class="stat-icon">
                <el-icon :size="20"><Warning /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-number">{{ formatNumber(summary.total_small_files) }}</div>
                <div class="stat-text">小文件数</div>
              </div>
            </div>

            <div class="stat-cell warning">
              <div class="stat-icon">
                <el-icon :size="20"><Coin /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-number">{{ smallFileSize }}</div>
                <div class="stat-text">占用空间</div>
              </div>
            </div>

            <div class="stat-cell info">
              <div class="stat-icon">
                <el-icon :size="20"><Timer /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-number">{{ wastedStorage }}</div>
                <div class="stat-text">浪费存储</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        class="impact-analysis"
        v-if="showImpact"
      >
        <div class="impact-title">
          <el-icon :size="14"><TrendCharts /></el-icon>
          <span>影响分析</span>
        </div>

        <div class="impact-metrics">
          <div class="impact-item">
            <div class="impact-label">性能影响</div>
            <div class="impact-bar">
              <el-progress
                :percentage="performanceImpact"
                color="#F56C6C"
                :show-text="false"
                stroke-width="6"
              />
              <span class="impact-value">{{ performanceImpact }}%</span>
            </div>
          </div>

          <div class="impact-item">
            <div class="impact-label">存储效率</div>
            <div class="impact-bar">
              <el-progress
                :percentage="storageWaste"
                color="#E6A23C"
                :show-text="false"
                stroke-width="6"
              />
              <span class="impact-value">{{ storageWaste }}%</span>
            </div>
          </div>

          <div class="impact-item">
            <div class="impact-label">查询延迟</div>
            <div class="impact-bar">
              <el-progress
                :percentage="queryLatency"
                color="#909399"
                :show-text="false"
                stroke-width="6"
              />
              <span class="impact-value">+{{ queryLatency }}%</span>
            </div>
          </div>
        </div>
      </div>

      <div
        class="optimization-suggestions"
        v-if="showSuggestions"
      >
        <div class="suggestions-title">
          <el-icon :size="14"><InfoFilled /></el-icon>
          <span>优化建议</span>
        </div>

        <div class="suggestion-list">
          <div
            class="suggestion-item"
            v-for="suggestion in suggestions"
            :key="suggestion.id"
          >
            <div
              class="suggestion-priority"
              :class="suggestion.priority"
            >
              <el-icon :size="12">
                <component :is="getPriorityIcon(suggestion.priority)" />
              </el-icon>
            </div>
            <div class="suggestion-content">
              <div class="suggestion-text">{{ suggestion.text }}</div>
              <div class="suggestion-impact">预计收益: {{ suggestion.impact }}</div>
            </div>
          </div>
        </div>
      </div>

      <div
        class="action-buttons"
        v-if="showActions"
      >
        <div class="primary-actions">
          <el-button
            type="danger"
            size="small"
            @click="$emit('start-merge')"
            :loading="merging"
          >
            <el-icon><Operation /></el-icon>
            开始合并
          </el-button>

          <el-button
            type="warning"
            size="small"
            @click="$emit('analyze-files')"
            :loading="analyzing"
          >
            <el-icon><Search /></el-icon>
            深度分析
          </el-button>
        </div>

        <!-- 扩展操作 -->
        <div
          class="extended-actions"
          v-if="showExtendedActions"
        >
          <el-button
            type="primary"
            size="small"
            @click="$emit('scan-tables')"
            :loading="scanning"
          >
            <el-icon><Refresh /></el-icon>
            扫描表
          </el-button>

          <el-button
            type="success"
            size="small"
            @click="$emit('view-tables')"
            :loading="loading"
          >
            <el-icon><View /></el-icon>
            查看表
          </el-button>
        </div>

        <el-dropdown @command="handleCommand">
          <el-button
            type="info"
            size="small"
          >
            更多操作<el-icon class="el-icon--right"><CaretBottom /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="schedule">定时合并</el-dropdown-item>
              <el-dropdown-item command="export">导出报告</el-dropdown-item>
              <el-dropdown-item command="settings">合并设置</el-dropdown-item>
              <el-dropdown-item
                divided
                command="view-trends"
                >查看趋势</el-dropdown-item
              >
              <el-dropdown-item command="batch-process">批量处理</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import {
    WarningFilled,
    Warning,
    Coin,
    Timer,
    TrendCharts,
    Operation,
    Search,
    CaretBottom,
    InfoFilled,
    CircleCheck,
    Bell,
    Refresh,
    View
  } from '@element-plus/icons-vue'
  import { useDashboardStore } from '@/stores/dashboard'
  import { useMonitoringStore } from '@/stores/monitoring'

  interface Props {
    showImpact?: boolean
    showSuggestions?: boolean
    showActions?: boolean
    showExtendedActions?: boolean
    merging?: boolean
    analyzing?: boolean
    scanning?: boolean
    loading?: boolean
  }

  const props = withDefaults(defineProps<Props>(), {
    showImpact: true,
    showSuggestions: true,
    showActions: true,
    showExtendedActions: false,
    merging: false,
    analyzing: false,
    scanning: false,
    loading: false
  })

  defineEmits<{
    'start-merge': []
    'analyze-files': []
    'scan-tables': []
    'view-tables': []
    'schedule-merge': []
    'export-report': []
    'merge-settings': []
  }>()

  const dashboardStore = useDashboardStore()
  const monitoringStore = useMonitoringStore()

  // 计算属性
  const summary = computed(() => dashboardStore.summary)

  const smallFileRatio = computed(() => {
    if (summary.value.total_files === 0) return 0
    return Math.round((summary.value.total_small_files / summary.value.total_files) * 100)
  })

  const smallFileSize = computed(() => {
    const sizeGB = summary.value.small_file_size_gb
    if (sizeGB >= 1000) {
      return `${(sizeGB / 1000).toFixed(1)} TB`
    } else if (sizeGB >= 1) {
      return `${sizeGB.toFixed(1)} GB`
    } else {
      return `${(sizeGB * 1024).toFixed(0)} MB`
    }
  })

  const wastedStorage = computed(() => {
    const wasteRatio = 0.3
    const wastedGB = summary.value.small_file_size_gb * wasteRatio
    if (wastedGB >= 1000) {
      return `${(wastedGB / 1000).toFixed(1)} TB`
    } else if (wastedGB >= 1) {
      return `${wastedGB.toFixed(1)} GB`
    } else {
      return `${(wastedGB * 1024).toFixed(0)} MB`
    }
  })

  const alertType = computed(() => {
    const ratio = smallFileRatio.value
    if (ratio >= 60) return 'danger'
    if (ratio >= 40) return 'warning'
    if (ratio >= 20) return 'info'
    return 'success'
  })

  const alertLevel = computed(() => {
    const ratio = smallFileRatio.value
    if (ratio >= 60) return '严重'
    if (ratio >= 40) return '警告'
    if (ratio >= 20) return '注意'
    return '正常'
  })

  const alertIcon = computed(() => {
    const ratio = smallFileRatio.value
    if (ratio >= 60) return WarningFilled
    if (ratio >= 40) return Warning
    if (ratio >= 20) return InfoFilled
    return CircleCheck
  })

  const severityClass = computed(() => {
    const ratio = smallFileRatio.value
    if (ratio >= 60) return 'critical'
    if (ratio >= 40) return 'high'
    if (ratio >= 20) return 'medium'
    return 'low'
  })

  const severityText = computed(() => {
    const ratio = smallFileRatio.value
    if (ratio >= 60) return '严重问题'
    if (ratio >= 40) return '高风险'
    if (ratio >= 20) return '中等风险'
    return '低风险'
  })

  const severityDescription = computed(() => {
    const ratio = smallFileRatio.value
    if (ratio >= 60) return '需要立即处理'
    if (ratio >= 40) return '建议尽快处理'
    if (ratio >= 20) return '建议定期处理'
    return '保持现状'
  })

  const ringStyle = computed(() => {
    const ratio = smallFileRatio.value
    const strokeDasharray = `${ratio * 2.83} 283`
    let color = '#67C23A'

    if (ratio >= 60) color = '#F56C6C'
    else if (ratio >= 40) color = '#E6A23C'
    else if (ratio >= 20) color = '#409EFF'

    return {
      '--stroke-dasharray': strokeDasharray,
      '--ring-color': color
    }
  })

  const performanceImpact = computed(() => Math.min(90, smallFileRatio.value * 1.5))
  const storageWaste = computed(() => Math.min(85, smallFileRatio.value * 1.2))
  const queryLatency = computed(() => Math.min(95, smallFileRatio.value * 2))

  // 优化建议
  const suggestions = computed(() => {
    const ratio = smallFileRatio.value
    const baseSuggestions = [
      { id: 1, text: '合并小文件到128MB以上', impact: '提升查询性能30%', priority: 'high' },
      { id: 2, text: '设置定时合并任务', impact: '降低维护成本50%', priority: 'medium' },
      { id: 3, text: '优化数据写入策略', impact: '减少小文件产生60%', priority: 'medium' }
    ]

    if (ratio >= 60) {
      baseSuggestions.unshift({
        id: 0,
        text: '立即停止新数据写入并紧急合并',
        impact: '避免系统性能进一步恶化',
        priority: 'critical'
      })
    }

    return baseSuggestions.slice(0, ratio >= 40 ? 4 : 3)
  })

  // 方法
  function formatNumber(num: number): string {
    return monitoringStore.formatNumber(num)
  }

  function getPriorityIcon(priority: string) {
    switch (priority) {
      case 'critical':
        return WarningFilled
      case 'high':
        return Warning
      case 'medium':
        return InfoFilled
      default:
        return Bell
    }
  }

  function handleCommand(command: string) {
    switch (command) {
      case 'schedule':
        // emit('schedule-merge')
        break
      case 'export':
        // emit('export-report')
        break
      case 'settings':
        // emit('merge-settings')
        break
    }
  }
</script>

<style scoped>
  .small-file-card {
    border-radius: 12px;
    transition: all 0.3s ease;
    background: linear-gradient(135deg, #fd79a8 0%, #fdcb6e 100%);
    color: white;
  }

  .small-file-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(253, 121, 168, 0.25);
  }

  .small-file-card :deep(.el-card__header) {
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

  .problem-overview {
    display: grid;
    grid-template-columns: 140px 1fr;
    gap: 20px;
    margin-bottom: 20px;
  }

  .severity-indicator {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  .severity-chart {
    position: relative;
  }

  .chart-ring {
    width: 90px;
    height: 90px;
    border-radius: 50%;
    background: conic-gradient(
      var(--ring-color) 0deg calc(var(--stroke-dasharray, 0) * 1deg),
      rgba(255, 255, 255, 0.2) calc(var(--stroke-dasharray, 0) * 1deg) 360deg
    );
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }

  .chart-ring::before {
    content: '';
    position: absolute;
    width: 60px;
    height: 60px;
    background: linear-gradient(135deg, #fd79a8 0%, #fdcb6e 100%);
    border-radius: 50%;
  }

  .ring-center {
    position: relative;
    z-index: 1;
    text-align: center;
  }

  .center-ratio {
    font-size: 18px;
    font-weight: bold;
    color: white;
    line-height: 1;
  }

  .center-label {
    font-size: 9px;
    color: rgba(255, 255, 255, 0.8);
    margin-top: 2px;
  }

  .severity-level {
    text-align: center;
  }

  .level-text {
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 4px;
  }

  .level-desc {
    font-size: 11px;
    opacity: 0.8;
  }

  .severity-level.critical {
    color: #ff6b6b;
  }

  .severity-level.high {
    color: #ffa726;
  }

  .severity-level.medium {
    color: #42a5f5;
  }

  .severity-level.low {
    color: #66bb6a;
  }

  .stat-grid {
    display: grid;
    grid-template-rows: repeat(3, 1fr);
    gap: 12px;
  }

  .stat-cell {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.1);
    transition: all 0.3s ease;
  }

  .stat-cell:hover {
    background: rgba(255, 255, 255, 0.15);
    transform: scale(1.02);
  }

  .stat-icon {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.2);
  }

  .stat-content {
    flex: 1;
  }

  .stat-number {
    font-size: 16px;
    font-weight: bold;
    color: white;
    line-height: 1.2;
  }

  .stat-text {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.8);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .impact-analysis,
  .optimization-suggestions {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
  }

  .impact-title,
  .suggestions-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 12px;
    color: rgba(255, 255, 255, 0.95);
  }

  .impact-metrics {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .impact-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .impact-label {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.8);
    min-width: 60px;
  }

  .impact-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    margin-left: 12px;
  }

  .impact-value {
    font-size: 11px;
    font-weight: bold;
    color: white;
    min-width: 35px;
  }

  .suggestion-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .suggestion-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 8px 0;
  }

  .suggestion-priority {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .suggestion-priority.critical {
    background: #ff6b6b;
  }

  .suggestion-priority.high {
    background: #ffa726;
  }

  .suggestion-priority.medium {
    background: #42a5f5;
  }

  .suggestion-priority.low {
    background: #66bb6a;
  }

  .suggestion-content {
    flex: 1;
  }

  .suggestion-text {
    font-size: 13px;
    color: white;
    font-weight: 500;
    line-height: 1.3;
    margin-bottom: 2px;
  }

  .suggestion-impact {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.7);
  }

  .action-buttons {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .primary-actions,
  .extended-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .action-buttons :deep(.el-button) {
    flex: 1;
    min-width: 80px;
    border: 1px solid rgba(255, 255, 255, 0.3);
  }

  .action-buttons :deep(.el-button--danger) {
    background: rgba(245, 108, 108, 0.3);
    border-color: rgba(245, 108, 108, 0.5);
  }

  .action-buttons :deep(.el-button--warning) {
    background: rgba(230, 162, 60, 0.3);
    border-color: rgba(230, 162, 60, 0.5);
  }

  .action-buttons :deep(.el-button--info) {
    background: rgba(64, 158, 255, 0.3);
    border-color: rgba(64, 158, 255, 0.5);
  }

  .action-buttons :deep(.el-button--primary) {
    background: rgba(64, 158, 255, 0.4);
    border-color: rgba(64, 158, 255, 0.6);
  }

  .action-buttons :deep(.el-button--success) {
    background: rgba(103, 194, 58, 0.3);
    border-color: rgba(103, 194, 58, 0.5);
  }

  @media (max-width: 768px) {
    .problem-overview {
      grid-template-columns: 1fr;
      gap: 16px;
    }

    .severity-indicator {
      flex-direction: row;
      justify-content: center;
      align-items: center;
      gap: 20px;
    }

    .stat-grid {
      grid-template-columns: 1fr;
      grid-template-rows: auto;
    }

    .action-buttons {
      flex-direction: column;
    }

    .impact-item {
      flex-direction: column;
      align-items: flex-start;
      gap: 6px;
    }

    .impact-bar {
      width: 100%;
      margin-left: 0;
    }
  }
</style>
