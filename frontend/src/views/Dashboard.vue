<template>
  <div class="dashboard">
    <!-- 简洁信息栏 -->
    <div class="dashboard-header">
      <div class="header-left">
        <div class="cluster-info">
          <el-icon class="cluster-icon"><Connection /></el-icon>
          <div class="cluster-details">
            <h1 class="cluster-name">{{ currentClusterName }}</h1>
            <span class="cluster-status" :class="clusterStatusClass">{{ clusterStatusText }}</span>
          </div>
        </div>
        
        <div class="key-metrics">
          <div class="metric-item">
            <span class="metric-value">{{ formatNumber(dashboardStore.summary.total_tables) }}</span>
            <span class="metric-label">总表数</span>
          </div>
          <div class="metric-item">
            <span class="metric-value danger">{{ formatNumber(dashboardStore.summary.problem_tables || 0) }}</span>
            <span class="metric-label">问题表</span>
          </div>
          <div class="metric-item">
            <span class="metric-value warning">{{ formatNumber(dashboardStore.summary.total_small_files) }}</span>
            <span class="metric-label">小文件数</span>
          </div>
        </div>
      </div>
      
      <div class="header-right">
        <div class="refresh-info" v-if="monitoringStore.isAutoRefreshEnabled">
          <el-icon><Timer /></el-icon>
          <span>{{ nextRefreshText }}</span>
        </div>
        
        <el-button 
          type="success" 
          @click="performBatchScan"
          :loading="isBatchScanning"
          :icon="Search"
          size="default"
          style="margin-right: 12px;"
        >
          {{ isBatchScanning ? '批量扫描中...' : '批量扫描所有数据库' }}
        </el-button>
        
        <el-button 
          type="primary" 
          @click="performRefresh"
          :loading="isRefreshing"
          :icon="Refresh"
          size="default"
        >
          {{ monitoringStore.isAutoRefreshEnabled ? '自动刷新中' : '立即刷新' }}
        </el-button>
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Timer, VideoPlay, VideoPause, Refresh, TrendCharts, List, Connection,
  Operation, Search
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
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}

/* 仪表盘头部 */
.dashboard-header {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.cluster-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cluster-icon {
  font-size: 24px;
  color: #409eff;
}

.cluster-details {
  display: flex;
  flex-direction: column;
}

.cluster-name {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.cluster-status {
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
  margin-top: 4px;
  font-weight: 500;
  width: fit-content;
}

.cluster-status.status-active {
  background: #f0f9ff;
  color: #67c23a;
}

.cluster-status.status-inactive {
  background: #fef0f0;
  color: #f56c6c;
}

.cluster-status.status-error {
  background: #fef0f0;
  color: #f56c6c;
}

.key-metrics {
  display: flex;
  gap: 24px;
  padding-left: 32px;
  border-left: 2px solid #e4e7ed;
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  color: #409eff;
  line-height: 1.2;
}

.metric-value.danger {
  color: #f56c6c;
}

.metric-value.warning {
  color: #e6a23c;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.refresh-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #6b7280;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 8px;
}

/* 主监控面板 */
.main-monitoring-panel {
  display: flex;
  gap: 20px;
  height: calc(100vh - 200px);
}

.panel-left {
  flex: 1;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.main-chart {
  height: 100%;
}

/* 右侧面板 */
.panel-right {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-panel {
  border: none;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.recent-tasks-panel {
  flex: 1;
  border: none;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

:deep(.el-card__header) {
  padding: 20px 20px 16px;
  border-bottom: 1px solid #e4e7ed;
}

:deep(.el-card__body) {
  padding: 20px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.panel-header .el-icon {
  color: #409eff;
}

.panel-header .el-button {
  margin-left: auto;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-buttons .el-button {
  height: 40px;
  font-size: 14px;
  font-weight: 500;
}

/* 任务列表 */
.task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  cursor: pointer;
  transition: all 0.2s ease;
}

.task-item:hover {
  background: #ecf5ff;
  border-color: #b3d8ff;
}

.task-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.task-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin: 0 0 4px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-table {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-status {
  flex-shrink: 0;
}

.no-tasks {
  text-align: center;
  color: #909399;
  font-size: 14px;
  padding: 40px 20px;
}

/* 响应式适配 */
@media (max-width: 1400px) {
  .panel-right {
    width: 280px;
  }
  
  .key-metrics {
    gap: 20px;
    padding-left: 24px;
  }
}

@media (max-width: 1200px) {
  .main-monitoring-panel {
    flex-direction: column;
    height: auto;
  }
  
  .panel-right {
    width: 100%;
    flex-direction: row;
    overflow-x: auto;
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

@media (max-width: 768px) {
  .dashboard {
    padding: 12px;
  }
  
  .dashboard-header {
    flex-direction: column;
    gap: 16px;
    padding: 16px;
    text-align: center;
  }
  
  .header-left {
    flex-direction: column;
    gap: 16px;
  }
  
  .key-metrics {
    padding-left: 0;
    border-left: none;
    border-top: 2px solid #e4e7ed;
    padding-top: 16px;
  }
  
  .cluster-name {
    font-size: 18px;
  }
  
  .metric-value {
    font-size: 20px;
  }
  
  .panel-right {
    flex-direction: column;
  }
  
  .main-monitoring-panel {
    gap: 12px;
  }
  
  .panel-right {
    width: 100%;
  }
  
  .action-panel,
  .recent-tasks-panel {
    min-width: auto;
  }
}

@media (max-width: 480px) {
  .dashboard {
    padding: 8px;
  }
  
  .dashboard-header {
    padding: 12px;
  }
  
  .key-metrics {
    gap: 16px;
  }
  
  .metric-value {
    font-size: 18px;
  }
  
  .refresh-info {
    font-size: 12px;
    padding: 6px 8px;
  }
  
  .panel-header {
    font-size: 14px;
  }
  
  :deep(.el-card__header) {
    padding: 16px 16px 12px;
  }
  
  :deep(.el-card__body) {
    padding: 16px;
  }
}
</style>