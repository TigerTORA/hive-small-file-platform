<template>
  <div class="dashboard" data-testid="dashboard-loaded">
    <!-- 增强信息栏 -->
    <div class="dashboard-header">
      <div class="header-left">
        <div class="cluster-info">
          <div class="cluster-icon-wrapper">
            <el-icon class="cluster-icon"><Connection /></el-icon>
            <div class="cluster-status-indicator" :class="clusterStatusClass"></div>
          </div>
          <div class="cluster-details">
            <h1 class="cluster-name">{{ currentClusterName }}</h1>
            <span class="cluster-status" :class="clusterStatusClass">
              <el-icon><CircleCheckFilled /></el-icon>
              {{ clusterStatusText }}
            </span>
          </div>
        </div>

        <div class="key-metrics">
          <div class="metric-item" v-for="metric in keyMetrics" :key="metric.key">
            <div class="metric-icon" :class="metric.type">
              <el-icon><component :is="metric.icon" /></el-icon>
            </div>
            <div class="metric-content">
              <span class="metric-value" :class="metric.type">{{ metric.value }}</span>
              <span class="metric-label">{{ metric.label }}</span>
              <div v-if="metric.trend" class="metric-trend" :class="metric.trend.type">
                <el-icon><component :is="metric.trend.icon" /></el-icon>
                <span>{{ metric.trend.value }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="header-right">
        <div class="refresh-info" v-if="monitoringStore.isAutoRefreshEnabled">
          <el-icon><Timer /></el-icon>
          <span>{{ nextRefreshText }}</span>
          <div class="refresh-progress">
            <div class="progress-bar" :style="{ width: refreshProgress + '%' }"></div>
          </div>
        </div>

        <div class="action-buttons">
          <el-button
            type="success"
            @click="performBatchScan"
            :loading="isBatchScanning"
            :icon="Search"
            size="default"
            class="action-button"
          >
            {{ isBatchScanning ? '批量扫描中...' : '批量扫描' }}
          </el-button>

          <el-button
            type="primary"
            @click="performRefresh"
            :loading="isRefreshing"
            :icon="Refresh"
            size="default"
            class="action-button"
          >
            {{ monitoringStore.isAutoRefreshEnabled ? '自动刷新中' : '立即刷新' }}
          </el-button>

          <el-button
            v-if="isEnabled('fullscreenMode')"
            :icon="FullScreen"
            circle
            size="default"
            @click="enterBigScreenMode"
            title="进入大屏模式"
            class="fullscreen-button"
          />
        </div>
      </div>
    </div>

    <!-- 主要监控面板 - 表文件数监控 -->
    <div class="main-monitoring-panel">
      <div class="panel-left">
        <TableFileCountChart 
          :cluster-id="monitoringStore.settings.selectedCluster"
          :refreshing="isRefreshing"
          @refresh="performRefresh"
          @table-analyze="handleTableAnalysis"
          class="main-chart"
        />
      </div>
      
      <div class="panel-right">
        <!-- 快速操作面板 -->
        <el-card class="action-panel" shadow="hover">
          <template #header>
            <div class="panel-header">
              <el-icon><Operation /></el-icon>
              <span>快速操作</span>
            </div>
          </template>
          
          <div class="action-buttons">
            <el-button 
              type="primary" 
              size="default"
              @click="handleScanTables"
              :loading="scanningTables"
              :icon="Search"
              block
            >
              扫描表
            </el-button>
            
            <el-button 
              type="danger" 
              size="default"
              @click="handleStartMerge"
              :loading="mergingFiles"
              :icon="Operation"
              block
            >
              开始合并
            </el-button>
            
            <el-button 
              type="warning" 
              size="default"
              @click="handleAnalyzeFiles"
              :loading="analyzingFiles"
              :icon="TrendCharts"
              block
            >
              深度分析
            </el-button>
          </div>
        </el-card>

        <!-- 最近任务 -->
        <el-card class="recent-tasks-panel" shadow="hover">
          <template #header>
            <div class="panel-header">
              <el-icon><List /></el-icon>
              <span>最近任务</span>
              <el-button 
                type="text" 
                size="small" 
                @click="handleViewAllTasks"
              >
                查看全部
              </el-button>
            </div>
          </template>
          
          <div class="task-list">
            <div 
              v-for="task in dashboardStore.recentTasks.slice(0, 5)" 
              :key="task.id"
              class="task-item"
              @click="handleViewTask(task)"
            >
              <div class="task-info">
                <div class="task-name">{{ task.task_name }}</div>
                <div class="task-table">{{ task.table_name }}</div>
              </div>
              <div class="task-status">
                <el-tag :type="getStatusType(task.status)" size="small">
                  {{ getStatusText(task.status) }}
                </el-tag>
              </div>
            </div>
            
            <div v-if="!dashboardStore.recentTasks.length" class="no-tasks">
              暂无任务记录
            </div>
          </div>
        </el-card>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, inject } from 'vue'
import { useRouter } from 'vue-router'
import {
  Timer, Refresh, TrendCharts, List, Connection, Operation, Search,
  CircleCheckFilled, FullScreen, Grid, Warning, Document,
  ArrowUp, ArrowDown, InfoFilled
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ClusterCard, TableCard, FileCard, SmallFileCard,
  TrendChart, DistributionChart, TableFileCountChart
} from '@/components'
import DraggableGrid from '@/components/layout/DraggableGrid.vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useMonitoringStore } from '@/stores/monitoring'
import { useDashboardLayoutStore, type GridItemLayout } from '@/stores/dashboardLayout'
import { useRealtime } from '@/composables/useRealtime'
import { tasksApi } from '@/api/tasks'

// 注入特性开关
const featureFlagContext = inject('featureFlags') as any
const isEnabled = featureFlagContext?.isEnabled || (() => false)

const router = useRouter()
const dashboardStore = useDashboardStore()
const monitoringStore = useMonitoringStore()
const layoutStore = useDashboardLayoutStore()

const { 
  isRefreshing, 
  nextRefreshIn,
  performRefresh,
  startAutoRefresh,
  stopAutoRefresh 
} = useRealtime()

// 计算属性
const nextRefreshText = computed(() => {
  if (!monitoringStore.isAutoRefreshEnabled) return ''
  if (nextRefreshIn.value <= 0) return '刷新中...'
  return `${nextRefreshIn.value}秒后刷新`
})

// 刷新进度百分比
const refreshProgress = computed(() => {
  if (!monitoringStore.isAutoRefreshEnabled) return 0
  const total = 30 // 假设30秒刷新间隔
  const remaining = nextRefreshIn.value
  return Math.max(0, ((total - remaining) / total) * 100)
})

// 关键指标数据
const keyMetrics = computed(() => {
  const summary = dashboardStore.summary
  return [
    {
      key: 'total_tables',
      label: '总表数',
      value: formatNumber(summary.total_tables),
      icon: Grid,
      type: 'primary',
      trend: {
        type: 'up',
        icon: ArrowUp,
        value: '+12%'
      }
    },
    {
      key: 'problem_tables',
      label: '问题表',
      value: formatNumber(summary.problem_tables || 0),
      icon: Warning,
      type: 'danger',
      trend: {
        type: 'down',
        icon: ArrowDown,
        value: '-8%'
      }
    },
    {
      key: 'small_files',
      label: '小文件数',
      value: formatNumber(summary.total_small_files),
      icon: Document,
      type: 'warning',
      trend: {
        type: 'down',
        icon: ArrowDown,
        value: '-15%'
      }
    }
  ]
})

// 集群相关信息
const currentClusterName = computed(() => {
  const clusters = dashboardStore.clusterStats
  const selectedId = monitoringStore.settings.selectedCluster
  const cluster = clusters.find(c => c.id === selectedId)
  return cluster?.name || '默认集群'
})

const clusterStatusText = computed(() => {
  const clusters = dashboardStore.clusterStats
  const selectedId = monitoringStore.settings.selectedCluster
  const cluster = clusters.find(c => c.id === selectedId)
  const statusMap = {
    'active': '运行中',
    'inactive': '已停止', 
    'error': '异常'
  }
  return statusMap[cluster?.status || 'active'] || '运行中'
})

const clusterStatusClass = computed(() => {
  const clusters = dashboardStore.clusterStats
  const selectedId = monitoringStore.settings.selectedCluster
  const cluster = clusters.find(c => c.id === selectedId)
  return `status-${cluster?.status || 'active'}`
})

// 操作状态
const scanningTables = computed(() => false) // TODO: 实现表扫描状态
const mergingFiles = computed(() => false) // TODO: 实现文件合并状态  
const analyzingFiles = computed(() => false) // TODO: 实现文件分析状态

// 进入大屏模式
const enterBigScreenMode = () => {
  const clusterId = monitoringStore.settings.selectedCluster
  router.push({
    path: '/big-screen',
    query: { cluster: clusterId }
  })
}

// 事件处理
function handleClusterChange(clusterId: number) {
  performRefresh()
}

function handleScanTables() {
  ElMessage.info('开始扫描表...')
  // TODO: 实现表扫描逻辑
}

function handleViewTables() {
  router.push('/tables')
}

function handleStartMerge() {
  // 直接跳转到任务管理页面，用户可以在那里创建合并任务
  router.push('/tasks')
}

function handleAnalyzeFiles() {
  ElMessage.info('开始深度分析...')
  // TODO: 实现深度分析逻辑
}

function handleExportTrend() {
  ElMessage.info('导出趋势图表...')
  // TODO: 实现图表导出
}

function handleExportDistribution() {
  ElMessage.info('导出分布图表...')
  // TODO: 实现图表导出
}

function handlePeriodChange(days: number) {
  dashboardStore.loadTrends(monitoringStore.settings.selectedCluster, days)
}

function handleTrendChartClick(params: any) {
  console.log('Trend chart clicked:', params)
  // TODO: 处理图表点击事件
}

function handleDistributionChartClick(params: any) {
  console.log('Distribution chart clicked:', params)
  // TODO: 处理图表点击事件
}

function handleDistributionRowClick(item: any, index: number) {
  console.log('Distribution row clicked:', item, index)
  // TODO: 处理分布表格行点击
}

function handleTableRowClick(row: any) {
  // 跳转到表详情页
  const clusterId = row.cluster_id || monitoringStore.settings.selectedCluster || 1
  router.push(`/tables/${clusterId}/${row.database_name}/${row.table_name}`)
}

function handleTableAnalysis(row: any) {
  const tableName = row.table_name || `${row.database_name}.${row.table_name}`
  ElMessage.info(`分析表 ${tableName}...`)
  // TODO: 实现表分析逻辑
}

function handleViewAllTables() {
  router.push('/tables')
}

function handleTaskRowClick(row: any) {
  router.push(`/tasks/${row.id}`)
}

function handleViewTask(row: any) {
  router.push(`/tasks/${row.id}`)
}

function handleViewAllTasks() {
  router.push('/tasks')
}

function handleSelectCluster(cluster: any) {
  monitoringStore.setSelectedCluster(cluster.id)
  performRefresh()
}

// 格式化函数
function formatNumber(num: number): string {
  return monitoringStore.formatNumber(num)
}

function formatTime(time: string): string {
  return monitoringStore.formatDate(time)
}

function getStatusType(status: string): string {
  const statusMap: Record<string, string> = {
    'pending': 'info',
    'running': 'warning',
    'success': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    'pending': '等待中',
    'running': '运行中',
    'success': '成功',
    'failed': '失败'
  }
  return statusMap[status] || status
}

function getProgressColor(ratio: number): string {
  if (ratio >= 60) return '#F56C6C'
  if (ratio >= 40) return '#E6A23C'
  return '#67C23A'
}

function getClusterStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    'active': '运行中',
    'inactive': '已停止',
    'error': '异常'
  }
  return statusMap[status] || status
}

// 布局相关事件处理
function handleLayoutChange(newLayout: GridItemLayout[]) {
  layoutStore.updateLayout(newLayout)
}

function handleEditModeChange(editMode: boolean) {
  layoutStore.setEditMode(editMode)
  
  if (editMode) {
    ElMessage.info('已进入布局编辑模式，可以拖拽和调整卡片大小')
  } else {
    ElMessage.success('布局已锁定')
  }
}

function handleLayoutReset() {
  ElMessage.success('布局已重置为默认配置')
}

// 批量扫描功能
const isBatchScanning = ref(false)

async function performBatchScan() {
  if (isBatchScanning.value) return
  
  const clusterId = monitoringStore.settings.selectedCluster
  if (!clusterId) {
    ElMessage.error('请先选择一个集群')
    return
  }

  try {
    const confirmed = await ElMessageBox.confirm(
      '批量扫描将对所有数据库进行小文件分析，可能需要较长时间。是否继续？',
      '批量扫描确认',
      {
        confirmButtonText: '确定扫描',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    if (confirmed) {
      isBatchScanning.value = true
      ElMessage.info('开始批量扫描所有数据库，请稍候...')

      const result = await tasksApi.scanAllDatabases(clusterId, 10)
      
      if (result.summary) {
        const summary = result.summary
        ElMessage.success(
          `批量扫描完成！共扫描 ${summary.total_databases} 个数据库，` +
          `${summary.total_tables_scanned} 个表，发现 ${summary.total_small_files} 个小文件 ` +
          `(小文件率: ${summary.small_file_ratio}%)`
        )
        
        // 重新加载仪表盘数据以显示最新结果
        await dashboardStore.loadAllData(clusterId)
        
      } else {
        ElMessage.success('批量扫描完成！')
      }
      
    }
  } catch (error: any) {
    console.error('批量扫描失败:', error)
    if (error.name !== 'cancel') { // 用户取消不显示错误
      ElMessage.error(`批量扫描失败: ${error.message || '未知错误'}`)
    }
  } finally {
    isBatchScanning.value = false
  }
}

// 生命周期
onMounted(async () => {
  // 初始化布局 store
  layoutStore.initialize()
  
  // 加载仪表盘数据
  await dashboardStore.loadAllData(monitoringStore.settings.selectedCluster)
})
</script>

@import '@/styles/design-tokens.scss';

<style scoped>
.dashboard {
  padding: var(--hive-space-5);
  background: var(--hive-bg-page);
  min-height: 100vh;
  transition: all var(--hive-duration-300) var(--hive-ease-out);
}

/* 仪表盘头部 - 使用设计系统 */
.dashboard-header {
  background: var(--hive-card-bg);
  border-radius: var(--hive-card-radius);
  padding: var(--hive-space-6);
  margin-bottom: var(--hive-space-5);
  box-shadow: var(--hive-card-shadow);
  border: 1px solid var(--hive-card-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: var(--hive-transition-all);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--hive-space-8);
}

.cluster-info {
  display: flex;
  align-items: center;
  gap: var(--hive-space-4);
}

.cluster-icon-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: var(--hive-gradient-primary);
  border-radius: var(--hive-radius-xl);
  box-shadow: var(--hive-shadow-base);
}

.cluster-icon {
  font-size: 24px;
  color: var(--hive-white);
}

.cluster-status-indicator {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 16px;
  height: 16px;
  border-radius: var(--hive-radius-full);
  border: 2px solid var(--hive-white);
  box-shadow: var(--hive-shadow-light);
}

.cluster-status-indicator.status-active {
  background: var(--hive-status-online);
}

.cluster-status-indicator.status-inactive {
  background: var(--hive-status-offline);
}

.cluster-status-indicator.status-error {
  background: var(--hive-status-offline);
}

.cluster-details {
  display: flex;
  flex-direction: column;
  gap: var(--hive-space-1);
}

.cluster-name {
  margin: 0;
  font-size: var(--hive-font-size-xl);
  font-weight: var(--hive-font-weight-semibold);
  color: var(--hive-text-primary);
  line-height: var(--hive-line-height-tight);
}

.cluster-status {
  display: flex;
  align-items: center;
  gap: var(--hive-space-1);
  font-size: var(--hive-font-size-sm);
  font-weight: var(--hive-font-weight-medium);
  padding: var(--hive-space-1) var(--hive-space-3);
  border-radius: var(--hive-radius-base);
  width: fit-content;
  transition: var(--hive-transition-all);
}

.cluster-status.status-active {
  background: rgba(82, 196, 26, 0.1);
  color: var(--hive-status-online);
}

.cluster-status.status-inactive {
  background: rgba(255, 77, 79, 0.1);
  color: var(--hive-status-offline);
}

.cluster-status.status-error {
  background: rgba(255, 77, 79, 0.1);
  color: var(--hive-status-offline);
}

/* 关键指标 */
.key-metrics {
  display: flex;
  gap: var(--hive-space-6);
  padding-left: var(--hive-space-8);
  border-left: 2px solid var(--hive-border-light);
}

.metric-item {
  display: flex;
  align-items: center;
  gap: var(--hive-space-3);
  padding: var(--hive-space-4);
  background: var(--hive-gray-50);
  border-radius: var(--hive-radius-lg);
  border: 1px solid var(--hive-border-lighter);
  transition: var(--hive-transition-all);
  min-width: 120px;
}

.metric-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--hive-shadow-base);
}

.metric-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--hive-radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.metric-icon.primary {
  background: rgba(64, 158, 255, 0.1);
  color: var(--hive-primary);
}

.metric-icon.danger {
  background: rgba(245, 108, 108, 0.1);
  color: var(--hive-danger);
}

.metric-icon.warning {
  background: rgba(230, 162, 60, 0.1);
  color: var(--hive-warning);
}

.metric-content {
  display: flex;
  flex-direction: column;
  gap: var(--hive-space-1);
}

.metric-value {
  font-size: var(--hive-font-size-2xl);
  font-weight: var(--hive-font-weight-bold);
  line-height: var(--hive-line-height-tight);
}

.metric-value.primary {
  color: var(--hive-primary);
}

.metric-value.danger {
  color: var(--hive-danger);
}

.metric-value.warning {
  color: var(--hive-warning);
}

.metric-label {
  font-size: var(--hive-font-size-xs);
  color: var(--hive-text-secondary);
  font-weight: var(--hive-font-weight-medium);
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: var(--hive-space-1);
  font-size: var(--hive-font-size-xs);
  font-weight: var(--hive-font-weight-medium);
}

.metric-trend.up {
  color: var(--hive-success);
}

.metric-trend.down {
  color: var(--hive-danger);
}

/* 头部右侧 */
.header-right {
  display: flex;
  align-items: center;
  gap: var(--hive-space-4);
}

.refresh-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--hive-space-2);
  font-size: var(--hive-font-size-sm);
  color: var(--hive-text-secondary);
  padding: var(--hive-space-3) var(--hive-space-4);
  background: var(--hive-gray-50);
  border-radius: var(--hive-radius-lg);
  border: 1px solid var(--hive-border-lighter);
  min-width: 120px;
}

.refresh-progress {
  width: 100%;
  height: 4px;
  background: var(--hive-border-light);
  border-radius: var(--hive-radius-full);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--hive-gradient-primary);
  border-radius: var(--hive-radius-full);
  transition: width var(--hive-duration-300) var(--hive-ease-out);
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: var(--hive-space-3);
}

.action-button {
  height: 40px;
  font-weight: var(--hive-font-weight-medium);
  border-radius: var(--hive-radius-lg);
  box-shadow: var(--hive-shadow-light);
  transition: var(--hive-transition-all);
}

.action-button:hover {
  transform: translateY(-1px);
  box-shadow: var(--hive-shadow-base);
}

.fullscreen-button {
  width: 40px;
  height: 40px;
  border-radius: var(--hive-radius-lg);
  box-shadow: var(--hive-shadow-light);
  transition: var(--hive-transition-all);
}

.fullscreen-button:hover {
  transform: translateY(-1px);
  box-shadow: var(--hive-shadow-base);
}

/* 主监控面板 - 使用设计系统 */
.main-monitoring-panel {
  display: flex;
  gap: var(--hive-space-5);
  height: calc(100vh - 200px);
  transition: var(--hive-transition-all);
}

.panel-left {
  flex: 1;
  background: var(--hive-card-bg);
  border-radius: var(--hive-card-radius);
  box-shadow: var(--hive-card-shadow);
  border: 1px solid var(--hive-card-border);
  overflow: hidden;
  transition: var(--hive-transition-all);
}

.panel-left:hover {
  box-shadow: var(--hive-shadow-dark);
}

.main-chart {
  height: 100%;
  transition: var(--hive-transition-all);
}

/* 右侧面板 - 使用设计系统 */
.panel-right {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: var(--hive-space-4);
}

.action-panel {
  border: 1px solid var(--hive-card-border);
  border-radius: var(--hive-card-radius);
  box-shadow: var(--hive-card-shadow);
  background: var(--hive-card-bg);
  transition: var(--hive-transition-all);
}

.action-panel:hover {
  box-shadow: var(--hive-shadow-dark);
}

.recent-tasks-panel {
  flex: 1;
  border: 1px solid var(--hive-card-border);
  border-radius: var(--hive-card-radius);
  box-shadow: var(--hive-card-shadow);
  background: var(--hive-card-bg);
  transition: var(--hive-transition-all);
}

.recent-tasks-panel:hover {
  box-shadow: var(--hive-shadow-dark);
}

:deep(.el-card__header) {
  padding: var(--hive-space-5) var(--hive-space-5) var(--hive-space-4);
  border-bottom: 1px solid var(--hive-border-light);
  background: var(--hive-card-bg);
}

:deep(.el-card__body) {
  padding: var(--hive-space-5);
  background: var(--hive-card-bg);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--hive-space-2);
  font-size: var(--hive-font-size-lg);
  font-weight: var(--hive-font-weight-semibold);
  color: var(--hive-text-primary);
  line-height: var(--hive-line-height-tight);
}

.panel-header .el-icon {
  color: var(--hive-primary);
  font-size: var(--hive-font-size-lg);
}

.panel-header .el-button {
  margin-left: auto;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: var(--hive-space-3);
}

.action-buttons .el-button {
  height: var(--hive-button-height-md);
  font-size: var(--hive-font-size-sm);
  font-weight: var(--hive-font-weight-medium);
  border-radius: var(--hive-button-radius);
  transition: var(--hive-transition-all);
}

.action-buttons .el-button:hover {
  transform: translateY(-1px);
  box-shadow: var(--hive-shadow-base);
}

/* 任务列表 - 使用设计系统 */
.task-list {
  display: flex;
  flex-direction: column;
  gap: var(--hive-space-2);
  max-height: 400px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--hive-border-base) transparent;
}

.task-list::-webkit-scrollbar {
  width: 6px;
}

.task-list::-webkit-scrollbar-track {
  background: transparent;
}

.task-list::-webkit-scrollbar-thumb {
  background: var(--hive-border-base);
  border-radius: var(--hive-radius-full);
}

.task-list::-webkit-scrollbar-thumb:hover {
  background: var(--hive-border-dark);
}

.task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--hive-space-3);
  background: var(--hive-bg-secondary);
  border-radius: var(--hive-radius-lg);
  border: 1px solid var(--hive-border-light);
  cursor: pointer;
  transition: var(--hive-transition-all);
}

.task-item:hover {
  background: rgba(64, 158, 255, 0.05);
  border-color: var(--hive-primary-light);
  transform: translateY(-1px);
  box-shadow: var(--hive-shadow-light);
}

.task-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  gap: var(--hive-space-1);
}

.task-name {
  font-size: var(--hive-font-size-sm);
  font-weight: var(--hive-font-weight-medium);
  color: var(--hive-text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: var(--hive-line-height-tight);
}

.task-table {
  font-size: var(--hive-font-size-xs);
  color: var(--hive-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: var(--hive-font-weight-normal);
}

.task-status {
  flex-shrink: 0;
}

.no-tasks {
  text-align: center;
  color: var(--hive-text-secondary);
  font-size: var(--hive-font-size-sm);
  font-weight: var(--hive-font-weight-normal);
  padding: var(--hive-space-10) var(--hive-space-5);
  border-radius: var(--hive-radius-lg);
  background: var(--hive-bg-secondary);
}

/* 响应式适配 - 使用设计系统断点 */
@media (max-width: var(--hive-breakpoint-xl)) {
  .panel-right {
    width: 280px;
  }

  .key-metrics {
    gap: var(--hive-space-5);
    padding-left: var(--hive-space-6);
  }
}

@media (max-width: var(--hive-breakpoint-lg)) {
  .main-monitoring-panel {
    flex-direction: column;
    height: auto;
    gap: var(--hive-space-4);
  }

  .panel-right {
    width: 100%;
    flex-direction: row;
    overflow-x: auto;
    gap: var(--hive-space-4);
  }

  .action-panel,
  .recent-tasks-panel {
    min-width: 280px;
    flex: none;
  }

  .recent-tasks-panel {
    flex: 1;
    min-width: 320px;
  }
}

@media (max-width: var(--hive-breakpoint-sm)) {
  .dashboard {
    padding: var(--hive-space-3);
  }

  .dashboard-header {
    flex-direction: column;
    gap: var(--hive-space-4);
    padding: var(--hive-card-padding);
    text-align: center;
  }

  .header-left {
    flex-direction: column;
    gap: var(--hive-space-4);
  }

  .key-metrics {
    padding-left: 0;
    border-left: none;
    border-top: 2px solid var(--hive-border-light);
    padding-top: var(--hive-space-4);
  }

  .cluster-name {
    font-size: var(--hive-font-size-lg);
  }

  .metric-value {
    font-size: var(--hive-font-size-xl);
  }

  .panel-right {
    flex-direction: column;
    gap: var(--hive-space-4);
  }

  .main-monitoring-panel {
    gap: var(--hive-space-3);
  }

  .action-panel,
  .recent-tasks-panel {
    min-width: auto;
  }
}

@media (max-width: var(--hive-breakpoint-xs)) {
  .dashboard {
    padding: var(--hive-space-2);
  }

  .dashboard-header {
    padding: var(--hive-space-3);
  }

  .key-metrics {
    gap: var(--hive-space-4);
    flex-direction: column;
    align-items: center;
  }

  .metric-item {
    min-width: auto;
    width: 100%;
    justify-content: center;
  }

  .metric-value {
    font-size: var(--hive-font-size-lg);
  }

  .refresh-info {
    font-size: var(--hive-font-size-xs);
    padding: var(--hive-space-2) var(--hive-space-3);
    min-width: auto;
  }

  .panel-header {
    font-size: var(--hive-font-size-sm);
  }

  :deep(.el-card__header) {
    padding: var(--hive-space-4) var(--hive-space-4) var(--hive-space-3);
  }

  :deep(.el-card__body) {
    padding: var(--hive-space-4);
  }

  .action-buttons .el-button {
    height: var(--hive-button-height-sm);
    font-size: var(--hive-font-size-xs);
  }
}
</style>