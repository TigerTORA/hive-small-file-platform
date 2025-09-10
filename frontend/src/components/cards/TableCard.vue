<template>
  <el-card class="table-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon class="header-icon" :size="20">
            <Grid />
          </el-icon>
          <span class="header-title">表统计</span>
        </div>
        <div class="header-right">
          <el-tooltip content="监控覆盖率" placement="top">
            <div class="coverage-badge">
              <span class="coverage-percent">{{ monitoringCoverage }}%</span>
            </div>
          </el-tooltip>
        </div>
      </div>
    </template>

    <div class="card-content">
      <div class="metrics-grid">
        <div class="metric-item primary">
          <div class="metric-icon">
            <el-icon :size="24"><Grid /></el-icon>
          </div>
          <div class="metric-info">
            <div class="metric-value">{{ formatNumber(totalTables) }}</div>
            <div class="metric-label">总表数</div>
          </div>
        </div>

        <div class="metric-item success">
          <div class="metric-icon">
            <el-icon :size="24"><View /></el-icon>
          </div>
          <div class="metric-info">
            <div class="metric-value">{{ formatNumber(monitoredTables) }}</div>
            <div class="metric-label">已监控表</div>
          </div>
        </div>
      </div>

      <div class="progress-section">
        <div class="progress-header">
          <span class="progress-title">监控进度</span>
          <div class="progress-actions">
            <el-button 
              type="text" 
              size="small" 
              @click="$emit('refresh')"
              :loading="loading"
            >
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>
        
        <el-progress 
          :percentage="monitoringCoverage" 
          :color="coverageColor"
          stroke-width="10"
          class="coverage-progress"
        >
          <template #default="{ percentage }">
            <span class="progress-text">{{ percentage }}%</span>
          </template>
        </el-progress>
      </div>

      <div class="table-stats" v-if="showDetails">
        <div class="stat-row">
          <span class="stat-label">平均文件数</span>
          <span class="stat-value">{{ avgFilesPerTable }}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">平均大小</span>
          <span class="stat-value">{{ avgTableSize }}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">最近扫描</span>
          <span class="stat-value">{{ lastScanTime }}</span>
        </div>
      </div>

      <div class="quick-actions" v-if="showActions">
        <el-button 
          type="primary" 
          size="small" 
          @click="$emit('scan-tables')"
          :loading="scanning"
        >
          <el-icon><Search /></el-icon>
          扫描表
        </el-button>
        <el-button 
          type="default" 
          size="small" 
          @click="$emit('view-tables')"
        >
          <el-icon><View /></el-icon>
          查看详情
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Grid, View, Refresh, Search } from '@element-plus/icons-vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useMonitoringStore } from '@/stores/monitoring'

interface Props {
  showDetails?: boolean
  showActions?: boolean
  loading?: boolean
  scanning?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showDetails: true,
  showActions: true,
  loading: false,
  scanning: false
})

defineEmits<{
  refresh: []
  'scan-tables': []
  'view-tables': []
}>()

const dashboardStore = useDashboardStore()
const monitoringStore = useMonitoringStore()

// 计算属性
const totalTables = computed(() => dashboardStore.summary.total_tables)
const monitoredTables = computed(() => dashboardStore.summary.monitored_tables)

const monitoringCoverage = computed(() => {
  if (totalTables.value === 0) return 0
  return Math.round((monitoredTables.value / totalTables.value) * 100)
})

const coverageColor = computed(() => {
  const coverage = monitoringCoverage.value
  if (coverage >= 90) return '#67C23A'
  if (coverage >= 70) return '#E6A23C'
  if (coverage >= 50) return '#F56C6C'
  return '#909399'
})

const avgFilesPerTable = computed(() => {
  if (monitoredTables.value === 0) return '--'
  const avgFiles = Math.round(dashboardStore.summary.total_files / monitoredTables.value)
  return monitoringStore.formatNumber(avgFiles)
})

const avgTableSize = computed(() => {
  if (monitoredTables.value === 0) return '--'
  const avgSizeGB = dashboardStore.summary.total_size_gb / monitoredTables.value
  if (avgSizeGB >= 1) {
    return `${avgSizeGB.toFixed(1)} GB`
  } else {
    return `${(avgSizeGB * 1024).toFixed(0)} MB`
  }
})

const lastScanTime = computed(() => {
  if (!monitoringStore.lastRefreshTime) return '--'
  return monitoringStore.formatDate(monitoringStore.lastRefreshTime)
})

// 方法
function formatNumber(num: number): string {
  return monitoringStore.formatNumber(num)
}
</script>

<style scoped>
.table-card {
  border-radius: 12px;
  transition: all 0.3s ease;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.table-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.25);
}

.table-card :deep(.el-card__header) {
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

.coverage-badge {
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
}

.card-content {
  padding-top: 8px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  transition: all 0.3s ease;
}

.metric-item:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: scale(1.02);
}

.metric-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
}

.metric-info {
  flex: 1;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: white;
  line-height: 1.2;
}

.metric-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 2px;
}

.progress-section {
  margin-bottom: 20px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.progress-title {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
}

.progress-actions :deep(.el-button) {
  color: rgba(255, 255, 255, 0.8);
}

.progress-actions :deep(.el-button:hover) {
  color: white;
}

.coverage-progress {
  margin-bottom: 8px;
}

.progress-text {
  color: white;
  font-weight: bold;
  font-size: 12px;
}

.table-stats {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.stat-row:not(:last-child) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.stat-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
}

.stat-value {
  font-size: 13px;
  font-weight: 500;
  color: white;
}

.quick-actions {
  display: flex;
  gap: 8px;
}

.quick-actions :deep(.el-button) {
  flex: 1;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.quick-actions :deep(.el-button--primary) {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.4);
  color: white;
}

.quick-actions :deep(.el-button--primary:hover) {
  background: rgba(255, 255, 255, 0.3);
}

.quick-actions :deep(.el-button--default) {
  background: transparent;
  color: rgba(255, 255, 255, 0.9);
}

.quick-actions :deep(.el-button--default:hover) {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .metric-item {
    padding: 12px;
  }

  .metric-value {
    font-size: 20px;
  }

  .metric-icon {
    width: 40px;
    height: 40px;
  }

  .quick-actions {
    flex-direction: column;
  }
}
</style>