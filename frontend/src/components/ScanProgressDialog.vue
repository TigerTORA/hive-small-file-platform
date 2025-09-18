<template>
  <el-dialog
    v-model="visible"
    title="数据库扫描进度"
    width="800px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
  >
    <div class="scan-progress">
      <!-- 顶部状态提示条 -->
      <el-alert
        v-if="progress"
        :title="getStatusText(progress?.status)"
        :type="getStatusType(progress?.status) || 'info'"
        show-icon
        :closable="false"
        class="status-alert"
      />
      <div class="dialog-tools">
        <div class="left">
          <el-text
            size="small"
            type="info"
            >任务ID：</el-text
          >
          <el-text
            size="small"
            class="mono"
            >{{ shortTaskId }}</el-text
          >
          <el-button
            size="small"
            link
            @click="copyTaskId"
            class="cloudera-btn secondary"
            >复制</el-button
          >
        </div>
        <div class="right">
          <el-button
            size="small"
            @click="toggleFollow"
            class="cloudera-btn secondary"
            >{{ autoFollow ? '暂停跟随' : '继续跟随' }}</el-button
          >
          <el-button
            size="small"
            @click="copyLogs"
            :disabled="displayLogs.length === 0"
            class="cloudera-btn secondary"
            >复制日志</el-button
          >
          <el-button
            size="small"
            @click="exportLogs"
            :disabled="displayLogs.length === 0"
            class="cloudera-btn secondary"
            >导出TXT</el-button
          >
        </div>
      </div>
      <!-- Cloudera风格进度概览 -->
      <div class="cloudera-metrics-grid">
        <div class="cloudera-metric-card">
          <div class="metric-header">
            <div
              class="metric-icon"
              :class="getStatusType(progress?.status)"
            >
              <el-icon><InfoFilled /></el-icon>
            </div>
          </div>
          <div class="metric-value">
            <span
              class="cloudera-tag"
              :class="getStatusType(progress?.status)"
              >{{ getStatusText(progress?.status) }}</span
            >
          </div>
          <div class="metric-label">扫描状态</div>
        </div>

        <div class="cloudera-metric-card">
          <div class="metric-header">
            <div class="metric-icon primary">
              <el-icon><TrendCharts /></el-icon>
            </div>
          </div>
          <div class="metric-value">
            {{ progress?.completed_items || 0 }} / {{ progress?.total_items || 0 }}
          </div>
          <div class="metric-label">当前进度</div>
        </div>

        <div class="cloudera-metric-card">
          <div class="metric-header">
            <div class="metric-icon warning">
              <el-icon><Timer /></el-icon>
            </div>
          </div>
          <div class="metric-value">{{ formatTime(progress?.estimated_remaining_seconds) }}</div>
          <div class="metric-label">预计剩余</div>
        </div>
      </div>

      <!-- 进度条 -->
      <div class="progress-bar-section">
        <el-progress
          :percentage="progress?.progress_percentage || 0"
          :stroke-width="20"
          :status="getProgressStatus(progress?.status)"
        >
          <span class="progress-text">{{ progress?.progress_percentage || 0 }}%</span>
        </el-progress>
        <div
          class="current-task"
          v-if="progress?.current_item"
        >
          <el-text type="info">{{ progress.current_item }}</el-text>
        </div>
      </div>

      <!-- 统计信息 / 骨架占位 -->
      <div
        class="stats-section"
        v-if="progress?.status === 'completed' || hasStats"
      >
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic
              title="扫描表数"
              :value="scanStats.tables"
            />
          </el-col>
          <el-col :span="8">
            <el-statistic
              title="总文件数"
              :value="scanStats.files"
            />
          </el-col>
          <el-col :span="8">
            <el-statistic
              title="小文件数"
              :value="scanStats.smallFiles"
            />
          </el-col>
        </el-row>
      </div>
      <div
        v-else
        class="stats-skeleton"
      >
        <el-skeleton
          animated
          :rows="2"
        />
      </div>

      <!-- 实时日志 -->
      <div class="logs-section">
        <div class="logs-header">
          <h4>扫描日志</h4>
          <el-button
            size="small"
            @click="clearLogs"
            :disabled="progress?.status === 'running'"
            class="cloudera-btn secondary"
          >
            清空日志
          </el-button>
        </div>
        <div class="cloudera-table logs-container-wrapper">
          <div
            class="logs-container"
            ref="logsContainer"
          >
            <div
              v-for="(log, index) in displayLogs"
              :key="index"
              :class="['log-entry', levelClass(log.level)]"
            >
              <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
              <span
                class="cloudera-tag"
                :class="getLogType(log.level)"
                >{{ log.level }}</span
              >
              <span class="log-message">{{ log.message }}</span>
              <span
                v-if="log.database_name"
                class="log-db"
                >[{{ log.database_name }}]</span
              >
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button
          v-if="progress?.status === 'running'"
          @click="cancelTask"
          :loading="cancelling"
          class="cloudera-btn warning"
          >取消任务</el-button
        >
        <el-button
          @click="handleClose"
          :disabled="progress?.status === 'running'"
          class="cloudera-btn secondary"
        >
          {{ progress?.status === 'running' ? '扫描中...' : '关闭' }}
        </el-button>
        <el-button
          v-if="progress?.status === 'completed'"
          @click="viewResults"
          class="cloudera-btn primary"
        >
          查看结果
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
  import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { InfoFilled, Timer, TrendCharts } from '@element-plus/icons-vue'
  import api from '../api'
  import { scanTasksApi } from '@/api/scanTasks'

  interface ScanProgress {
    task_id: string
    status: string
    progress_percentage: number
    current_item?: string
    completed_items: number
    total_items: number
    estimated_remaining_seconds: number
    logs?: ScanLog[]
  }

  interface ScanLog {
    timestamp: string
    level: string
    message: string
    database_name?: string
    table_name?: string
  }

  const props = defineProps<{
    modelValue: boolean
    taskId?: string
  }>()

  const emit = defineEmits<{
    'update:modelValue': [value: boolean]
    completed: [taskId: string]
  }>()

  const visible = computed({
    get: () => props.modelValue,
    set: value => emit('update:modelValue', value)
  })

  const progress = ref<ScanProgress | null>(null)
  const displayLogs = ref<ScanLog[]>([])
  const logsContainer = ref<HTMLElement>()
  let pollInterval: NodeJS.Timeout | null = null
  const autoFollow = ref(true)
  const cancelling = ref(false)

  const scanStats = computed(() => ({
    tables:
      progress.value?.logs?.filter(log => log.level === 'INFO' && log.message.includes('扫描完成'))
        .length || 0,
    files: 0, // TODO: 从日志中提取文件统计
    smallFiles: 0
  }))

  const hasStats = computed(
    () => progress.value && (progress.value.completed_items > 0 || scanStats.value.tables > 0)
  )

  watch(
    () => props.taskId,
    newTaskId => {
      if (newTaskId && visible.value) {
        startPolling()
      }
    }
  )

  watch(visible, newVisible => {
    if (newVisible && props.taskId) {
      startPolling()
    } else {
      stopPolling()
    }
  })

  const startPolling = () => {
    stopPolling()
    fetchProgress()
    pollInterval = setInterval(fetchProgress, 2000) // 每2秒更新一次
  }

  const stopPolling = () => {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  const fetchProgress = async () => {
    if (!props.taskId) return

    try {
      // 获取扫描任务基本信息
      const taskData = await api.get(`/scan-tasks/${props.taskId}`)
      progress.value = taskData

      // 获取扫描任务日志
      try {
        const logsData = await api.get(`/scan-tasks/${props.taskId}/logs`)
        if (logsData && Array.isArray(logsData)) {
          // 最新在前，更新后滚动贴底确保可见
          displayLogs.value = [...logsData].reverse()
          await nextTick()
          scrollLogsToBottom()
        }
      } catch (logsError) {
        console.warn('Failed to fetch scan logs:', logsError)
        // 日志获取失败不影响主要功能
      }

      // 如果任务完成，停止轮询
      if (progress.value?.status === 'completed' || progress.value?.status === 'failed') {
        stopPolling()
        if (progress.value.status === 'completed') {
          ElMessage.success('扫描完成！')
          emit('completed', props.taskId!)
        } else if (progress.value.status === 'failed') {
          ElMessage.error('扫描失败')
        }
      }
    } catch (error: any) {
      console.error('Failed to fetch scan progress:', error)
      if (error.response?.status !== 404) {
        ElMessage.error('获取扫描进度失败')
      }
    }
  }

  const scrollLogsToBottom = () => {
    if (logsContainer.value && autoFollow.value) {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight
    }
  }

  // 简化：不再根据滚动位置判定，始终在更新后贴底

  const getStatusType = (status?: string) => {
    switch (status) {
      case 'running':
        return 'warning'
      case 'completed':
        return 'success'
      case 'failed':
        return 'danger'
      default:
        return 'info'
    }
  }

  const getStatusText = (status?: string) => {
    switch (status) {
      case 'pending':
        return '等待开始'
      case 'running':
        return '扫描中'
      case 'completed':
        return '已完成'
      case 'failed':
        return '失败'
      default:
        return '未知'
    }
  }

  const getProgressStatus = (status?: string) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'failed':
        return 'exception'
      default:
        return undefined
    }
  }

  const getLogType = (level: string) => {
    switch (level) {
      case 'INFO':
        return 'primary'
      case 'WARNING':
        return 'warning'
      case 'ERROR':
        return 'danger'
      default:
        return 'info'
    }
  }

  const levelClass = (level: string) => `log-${(level || '').toLowerCase()}`

  const formatTime = (seconds?: number) => {
    if (!seconds || seconds <= 0) return '计算中...'
    if (seconds < 60) return `${Math.round(seconds)}秒`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.round(seconds % 60)
    return `${minutes}分${remainingSeconds}秒`
  }

  const formatLogTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  const clearLogs = () => {
    displayLogs.value = []
  }

  const handleClose = () => {
    if (progress.value?.status === 'running') {
      ElMessage.warning('扫描进行中，无法关闭')
      return
    }
    stopPolling()
    visible.value = false
  }

  const viewResults = () => {
    // TODO: 导航到结果页面或显示结果对话框
    handleClose()
    ElMessage.info('查看结果功能开发中...')
  }

  const copyTaskId = async () => {
    if (!props.taskId) return
    try {
      await navigator.clipboard.writeText(props.taskId)
    } catch {}
    ElMessage.success('任务ID已复制')
  }

  const copyLogs = async () => {
    if (displayLogs.value.length === 0) return
    const text = displayLogs.value
      .map(
        l =>
          `${formatLogTime(l.timestamp)} [${l.level}] ${l.message}${l.database_name ? ' [' + l.database_name + ']' : ''}`
      )
      .join('\n')
    try {
      await navigator.clipboard.writeText(text)
    } catch {}
    ElMessage.success('日志已复制到剪贴板')
  }

  const toggleFollow = () => {
    autoFollow.value = !autoFollow.value
    if (autoFollow.value) scrollLogsToBottom()
  }

  const shortTaskId = computed(
    () => (props.taskId || '').slice(0, 8) + '…' + (props.taskId || '').slice(-6)
  )

  const exportLogs = () => {
    if (displayLogs.value.length === 0) return
    const text = displayLogs.value
      .map(
        l =>
          `${formatLogTime(l.timestamp)} [${l.level}] ${l.message}${l.database_name ? ' [' + l.database_name + ']' : ''}`
      )
      .join('\n')
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `scan-logs-${props.taskId || 'task'}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  onBeforeUnmount(() => {
    stopPolling()
  })

  const cancelTask = async () => {
    if (!props.taskId) return
    try {
      await ElMessageBox.confirm('确定要取消当前扫描任务吗？', '确认取消', { type: 'warning' })
    } catch {
      return
    }
    try {
      cancelling.value = true
      await scanTasksApi.cancel(props.taskId)
      ElMessage.success('已发送取消请求')
    } catch (e) {
      console.error('Cancel scan task failed:', e)
    } finally {
      cancelling.value = false
    }
  }
</script>

<style scoped>
  .scan-progress {
    padding: var(--space-6) 0;
  }

  .status-alert {
    margin-bottom: var(--space-4);
    border-radius: var(--radius-lg);
  }

  .dialog-tools {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-6);
    padding: var(--space-4);
    background: var(--gray-50);
    border-radius: var(--radius-lg);
    border: 1px solid var(--gray-200);
  }

  .dialog-tools .mono {
    font-family: var(--font-mono);
    background: var(--bg-primary);
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-md);
    border: 1px solid var(--gray-300);
  }

  .dialog-tools .left,
  .dialog-tools .right {
    display: flex;
    align-items: center;
    gap: var(--space-3);
  }

  .progress-bar-section {
    margin: var(--space-6) 0;
    text-align: center;
  }

  .progress-text {
    font-weight: var(--font-bold);
    color: var(--gray-900);
  }

  .current-task {
    margin-top: var(--space-4);
    padding: var(--space-3);
    background: var(--primary-50);
    border: 1px solid var(--primary-200);
    border-radius: var(--radius-lg);
    color: var(--primary-700);
  }

  .stats-section {
    margin: var(--space-6) 0;
    padding: var(--space-6);
    background: var(--gray-50);
    border-radius: var(--radius-xl);
    border: 1px solid var(--gray-200);
  }

  .logs-section {
    margin-top: var(--space-6);
  }

  .logs-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-4);
  }

  .logs-header h4 {
    margin: 0;
    color: var(--gray-900);
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
  }

  .logs-container-wrapper {
    border-radius: var(--radius-xl);
    overflow: hidden;
  }

  .logs-container {
    height: 300px;
    overflow-y: auto;
    padding: var(--space-4);
    background-color: #1a1d29;
    color: #ffffff;
    font-family: var(--font-mono);
    font-size: var(--text-sm);
  }

  .logs-container::-webkit-scrollbar {
    width: 6px;
  }

  .logs-container::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1);
  }

  .logs-container::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.3);
    border-radius: var(--radius-md);
  }

  .log-entry {
    display: flex;
    align-items: center;
    padding: var(--space-2) 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    gap: var(--space-3);
    transition: background-color var(--transition-fast);
  }

  .log-entry:last-child {
    border-bottom: none;
  }

  .log-entry:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .log-time {
    color: var(--nav-text-muted);
    white-space: nowrap;
    min-width: 80px;
    font-size: var(--text-xs);
  }

  .log-message {
    flex: 1;
    word-break: break-word;
    color: #ffffff;
  }

  .log-db {
    color: #66ccff;
    font-weight: var(--font-medium);
    font-size: var(--text-xs);
  }

  .log-info .log-message {
    color: #ffffff;
  }

  .log-warning .log-message {
    color: var(--warning-400);
  }

  .log-error .log-message {
    color: var(--danger-400);
  }

  .log-info {
    background: rgba(59, 130, 246, 0.05);
  }

  .log-warning {
    background: rgba(245, 158, 11, 0.05);
  }

  .log-error {
    background: rgba(239, 68, 68, 0.05);
  }

  .log-info {
    background: rgba(255, 255, 255, 0.02);
  }
  .log-warning {
    background: rgba(230, 162, 60, 0.08);
  }
  .log-error {
    background: rgba(245, 108, 108, 0.1);
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: var(--space-3);
    padding-top: var(--space-4);
  }
</style>
