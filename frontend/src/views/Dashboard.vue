<template>
  <div class="dashboard">
    <!-- Cloudera风格指标网格 -->
    <div class="cloudera-metrics-grid">
      <div
        v-for="(metric, index) in keyMetrics"
        :key="metric.key"
        class="cloudera-metric-card"
      >
        <div class="metric-header">
          <div class="metric-icon" :class="metric.type">
            <el-icon><component :is="metric.icon" /></el-icon>
          </div>
          <div class="metric-status" v-if="metric.trend">
            <el-icon><component :is="metric.trend.icon" /></el-icon>
            <span class="metric-trend" :class="metric.trend.type">{{ metric.trend.value }}</span>
          </div>
        </div>
        <div class="metric-value">{{ metric.value }}</div>
        <div class="metric-label">{{ metric.label }}</div>
      </div>

      <!-- 集群状态卡片 -->
      <div class="cloudera-metric-card cluster-status-card">
        <div class="metric-header">
          <div class="metric-icon info">
            <el-icon><Connection /></el-icon>
          </div>
          <div class="metric-status">
            <div class="status-dot" :class="clusterStatusClass"></div>
            <span class="cluster-status-text">{{ clusterStatusText }}</span>
          </div>
        </div>
        <div class="metric-value">{{ currentClusterName }}</div>
        <div class="metric-label">集群状态</div>
      </div>

      <!-- 刷新状态卡片 -->
      <div v-if="monitoringStore.isAutoRefreshEnabled" class="cloudera-metric-card refresh-card">
        <div class="metric-header">
          <div class="metric-icon info">
            <el-icon><Timer /></el-icon>
          </div>
          <el-button
            size="small"
            @click="performRefresh"
            :loading="isRefreshing"
            class="cloudera-btn secondary"
          >
            刷新
          </el-button>
        </div>
        <div class="metric-value">{{ nextRefreshText || '实时' }}</div>
        <div class="metric-label">自动刷新</div>
        <div class="refresh-progress" v-if="refreshProgress > 0">
          <div class="progress-bar" :style="{ width: refreshProgress + '%' }"></div>
        </div>
      </div>
    </div>

    <!-- 快速操作区域 -->
    <div class="action-section">
      <h3 class="section-title">
        <el-icon><Operation /></el-icon>
        快速操作
      </h3>
      <div class="action-grid">
        <el-button
          type="success"
          @click="performBatchScan"
          :loading="isBatchScanning"
          :icon="Search"
          size="large"
          class="cloudera-btn success"
        >
          {{ isBatchScanning ? '批量扫描中...' : '批量扫描' }}
        </el-button>

        <el-button
          type="danger"
          @click="handleStartMerge"
          :loading="mergingFiles"
          :icon="Operation"
          size="large"
          class="cloudera-btn danger"
        >
          开始合并
        </el-button>

        <el-button
          type="warning"
          @click="handleAnalyzeFiles"
          :loading="analyzingFiles"
          :icon="TrendCharts"
          size="large"
          class="cloudera-btn warning"
        >
          深度分析
        </el-button>

        <el-button
          v-if="isEnabled('fullscreenMode')"
          :icon="FullScreen"
          @click="enterBigScreenMode"
          size="large"
          class="cloudera-btn secondary"
        >
          大屏模式
        </el-button>
      </div>
    </div>

    <!-- 主要监控面板 -->
    <div class="main-monitoring-panel">
      <div class="panel-left">
        <div class="cloudera-table">
          <TableFileCountChart
            :cluster-id="monitoringStore.settings.selectedCluster"
            :refreshing="isRefreshing"
            @refresh="performRefresh"
            @table-analyze="handleTableAnalysis"
            class="main-chart"
          />
        </div>
      </div>

      <div class="panel-right">
        <!-- 最近任务面板 -->
        <div class="cloudera-table recent-tasks-panel">
          <div class="panel-header">
            <div class="header-title">
              <el-icon><List /></el-icon>
              <span>最近任务</span>
            </div>
            <el-button
              size="small"
              @click="handleViewAllTasks"
              class="cloudera-btn secondary"
            >
              查看全部
            </el-button>
          </div>

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
                <span class="cloudera-tag" :class="getStatusType(task.status)">
                  {{ getStatusText(task.status) }}
                </span>
              </div>
            </div>

            <div v-if="!dashboardStore.recentTasks.length" class="no-tasks">
              <el-icon><InfoFilled /></el-icon>
              <span>暂无任务记录</span>
            </div>
          </div>
        </div>
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
      type: 'info',
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
      type: 'info',
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

<style scoped>
.dashboard {
  padding: var(--space-3) var(--space-4) 400px var(--space-4);
  min-height: 150vh;
  overflow-y: visible;
  background: var(--bg-app);
  max-width: 1600px;
  margin: 0 auto;
}

/* 快速操作区域 */
.action-section {
  background: var(--bg-secondary);
  padding: var(--space-8);
  border-radius: var(--radius-2xl);
  margin-bottom: var(--space-10);
  border: 1px solid var(--gray-100);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
  margin-bottom: var(--space-8);
  padding-bottom: var(--space-4);
  border-bottom: 2px solid var(--gray-200);
}

.section-title .el-icon {
  color: var(--primary-500);
  font-size: var(--text-xl);
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-6);
}

/* 集群状态卡片特殊样式 */
.cluster-status-card .metric-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.cluster-status-text {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--gray-700);
}

.status-dot.status-active {
  background-color: var(--success-500);
}

.status-dot.status-inactive {
  background-color: var(--danger-500);
}

.status-dot.status-error {
  background-color: var(--danger-500);
}

/* 刷新卡片特殊样式 */
.refresh-card .refresh-progress {
  width: 100%;
  height: 4px;
  background: var(--gray-200);
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-top: var(--space-3);
}

.refresh-card .progress-bar {
  height: 100%;
  background: linear-gradient(135deg, var(--primary-500) 0%, var(--primary-600) 100%);
  border-radius: var(--radius-md);
  transition: width var(--transition-normal);
}

/* 主监控面板 */
.main-monitoring-panel {
  display: flex;
  gap: var(--space-8);
  min-height: 640px;
  margin-top: var(--space-4);
}

.panel-left {
  flex: 1;
}

.panel-right {
  width: 400px;
}

.main-chart {
  height: 100%;
  border-radius: var(--radius-xl);
}

/* 任务面板 */
.recent-tasks-panel {
  padding: var(--space-8);
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  border: 1px solid var(--gray-150);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-8);
  padding-bottom: var(--space-6);
  border-bottom: 2px solid var(--gray-200);
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
}

.header-title .el-icon {
  color: var(--primary-500);
  font-size: var(--text-lg);
}

/* 任务列表 */
.task-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding-right: var(--space-2);
}

.task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5);
  background: var(--bg-secondary);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-xl);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.task-item:hover {
  background: var(--bg-primary);
  border-color: var(--gray-300);
  transform: translateY(-1px);
  box-shadow: var(--elevation-2);
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--gray-900);
  margin-bottom: var(--space-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-table {
  font-size: var(--text-xs);
  color: var(--gray-600);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-status {
  flex-shrink: 0;
  margin-left: var(--space-3);
}

.no-tasks {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-16);
  color: var(--gray-500);
  font-size: var(--text-sm);
  text-align: center;
  background: var(--bg-tertiary);
  border-radius: var(--radius-xl);
  margin: var(--space-4);
}

.no-tasks .el-icon {
  font-size: var(--text-2xl);
  color: var(--gray-400);
}

/* Cloudera风格：简洁无动画 */

/* 响应式适配 */
@media (max-width: 1200px) {
  .main-monitoring-panel {
    flex-direction: column;
    gap: var(--space-6);
  }

  .panel-right {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .dashboard {
    padding: var(--space-4);
  }

  .action-grid {
    grid-template-columns: 1fr;
    gap: var(--space-3);
  }

  .main-monitoring-panel {
    gap: var(--space-4);
  }
}
</style>