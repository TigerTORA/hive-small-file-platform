<template>
  <el-dialog 
    v-model="visible" 
    title="数据库扫描进度"
    width="800px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
  >
    <div class="scan-progress">
      <!-- 进度概览 -->
      <div class="progress-overview">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card class="progress-card">
              <div class="progress-item">
                <div class="progress-label">扫描状态</div>
                <el-tag :type="getStatusType(progress?.status)">{{ getStatusText(progress?.status) }}</el-tag>
              </div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card class="progress-card">
              <div class="progress-item">
                <div class="progress-label">当前进度</div>
                <div class="progress-value">{{ progress?.completed_items || 0 }} / {{ progress?.total_items || 0 }}</div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card class="progress-card">
              <div class="progress-item">
                <div class="progress-label">预计剩余</div>
                <div class="progress-value">{{ formatTime(progress?.estimated_remaining_seconds) }}</div>
              </div>
            </el-card>
          </el-col>
        </el-row>
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
        <div class="current-task" v-if="progress?.current_item">
          <el-text type="info">{{ progress.current_item }}</el-text>
        </div>
      </div>

      <!-- 统计信息 -->
      <div class="stats-section" v-if="progress?.status === 'completed' || hasStats">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="扫描表数" :value="scanStats.tables" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="总文件数" :value="scanStats.files" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="小文件数" :value="scanStats.smallFiles" />
          </el-col>
        </el-row>
      </div>

      <!-- 实时日志 -->
      <div class="logs-section">
        <div class="logs-header">
          <h4>扫描日志</h4>
          <el-button size="small" @click="clearLogs" :disabled="progress?.status === 'running'">
            清空日志
          </el-button>
        </div>
        <div class="logs-container" ref="logsContainer" @scroll="handleLogsScroll">
          <div 
            v-for="(log, index) in displayLogs" 
            :key="index"
            :class="['log-entry', `log-${log.level.toLowerCase()}`]"
          >
            <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
            <el-tag 
              :type="getLogType(log.level)" 
              size="small"
              class="log-level"
            >
              {{ log.level }}
            </el-tag>
            <span class="log-message">{{ log.message }}</span>
            <span v-if="log.database_name" class="log-db">[{{ log.database_name }}]</span>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose" :disabled="progress?.status === 'running'">
          {{ progress?.status === 'running' ? '扫描中...' : '关闭' }}
        </el-button>
        <el-button 
          v-if="progress?.status === 'completed'" 
          type="primary" 
          @click="viewResults"
        >
          查看结果
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

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
  'completed': [taskId: string]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const progress = ref<ScanProgress | null>(null)
const displayLogs = ref<ScanLog[]>([])
const logsContainer = ref<HTMLElement>()
let pollInterval: NodeJS.Timeout | null = null
const autoStickBottom = ref(true)

const scanStats = computed(() => ({
  tables: progress.value?.logs?.filter(log => log.level === 'INFO' && log.message.includes('扫描完成')).length || 0,
  files: 0, // TODO: 从日志中提取文件统计
  smallFiles: 0
}))

const hasStats = computed(() => 
  progress.value && (progress.value.completed_items > 0 || scanStats.value.tables > 0)
)

watch(() => props.taskId, (newTaskId) => {
  if (newTaskId && visible.value) {
    startPolling()
  }
})

watch(visible, (newVisible) => {
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
    const data = await api.get(`/tables/scan-progress/${props.taskId}`)
    progress.value = data
    
    if (data.logs) {
      const shouldStick = isAtBottom()
      // 使用时间顺序（旧在上，新在下）
      displayLogs.value = [...data.logs]
      await nextTick()
      if (shouldStick) scrollLogsToBottom()
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
  if (logsContainer.value) {
    logsContainer.value.scrollTop = logsContainer.value.scrollHeight
  }
}

const isAtBottom = () => {
  const el = logsContainer.value
  if (!el) return true
  const threshold = 16 // px 容差
  return el.scrollTop + el.clientHeight >= el.scrollHeight - threshold
}

const handleLogsScroll = () => {
  autoStickBottom.value = isAtBottom()
}

const getStatusType = (status?: string) => {
  switch (status) {
    case 'running': return 'warning'
    case 'completed': return 'success'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

const getStatusText = (status?: string) => {
  switch (status) {
    case 'pending': return '等待开始'
    case 'running': return '扫描中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    default: return '未知'
  }
}

const getProgressStatus = (status?: string) => {
  switch (status) {
    case 'completed': return 'success'
    case 'failed': return 'exception'
    default: return undefined
  }
}

const getLogType = (level: string) => {
  switch (level) {
    case 'INFO': return 'primary'
    case 'WARNING': return 'warning'
    case 'ERROR': return 'danger'
    default: return 'info'
  }
}

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

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.scan-progress {
  padding: 20px 0;
}

.progress-overview {
  margin-bottom: 24px;
}

.progress-card {
  text-align: center;
}

.progress-item {
  padding: 12px;
}

.progress-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.progress-value {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}

.progress-bar-section {
  margin: 24px 0;
  text-align: center;
}

.progress-text {
  font-weight: bold;
}

.current-task {
  margin-top: 12px;
  padding: 8px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.stats-section {
  margin: 24px 0;
  padding: 20px;
  background-color: #fafafa;
  border-radius: 8px;
}

.logs-section {
  margin-top: 24px;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.logs-header h4 {
  margin: 0;
  color: #333;
}

.logs-container {
  height: 300px;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px;
  background-color: #1e1e1e;
  color: #ffffff;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
}

.log-entry {
  display: flex;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid #333;
  gap: 8px;
}

.log-entry:last-child {
  border-bottom: none;
}

.log-time {
  color: #888;
  white-space: nowrap;
  min-width: 80px;
}

.log-level {
  min-width: 60px;
}

.log-message {
  flex: 1;
  word-break: break-word;
}

.log-db {
  color: #66ccff;
  font-weight: bold;
}

.log-info .log-message {
  color: #ffffff;
}

.log-warning .log-message {
  color: #f0ad4e;
}

.log-error .log-message {
  color: #d9534f;
}

.dialog-footer {
  text-align: right;
}
</style>
