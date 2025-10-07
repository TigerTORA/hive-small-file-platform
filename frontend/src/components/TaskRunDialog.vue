<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="90vw"
    :style="{ maxWidth: '1280px' }"
    top="8vh"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
  >
    <div class="task-run">
      <!-- Header summary -->
      <div class="header-summary">
        <div class="meta">
          <el-tag size="small" :type="statusTagType">{{ statusText }}</el-tag>
          <span class="kv">任务ID</span><span class="mono">{{ shortId }}</span>
          <span v-if="run?.startedAt" class="kv">开始</span><span class="mono">{{ formatTime(run?.startedAt) }}</span>
          <span v-if="run?.finishedAt" class="kv">结束</span><span class="mono">{{ formatTime(run?.finishedAt) }}</span>
        </div>
        <div class="ops">
          <!-- 用户反馈：无新日志提示不需要，移除 --><!---->
          <el-button size="small" class="cloudera-btn secondary" @click="forceRefresh">刷新</el-button>
          <el-button
            v-if="canCancel"
            size="small"
            type="warning"
            @click="onCancel"
          >取消任务</el-button>
          <el-button size="small" class="cloudera-btn secondary" @click="copyId">复制ID</el-button>
          <el-button size="small" class="cloudera-btn secondary" @click="exportAllLogs" :disabled="(run?.logs?.length||0)===0">导出日志</el-button>
        </div>
      </div>

      <!-- Body: steps + details -->
      <div class="body">
        <div class="steps">
          <div
            v-for="s in run?.steps"
            :key="s.id"
            :class="['step', s.id===activeStepId ? 'active' : '', s.status]"
            @click="activeStepId = s.id"
          >
            <span class="dot" :class="s.status"></span>
            <div class="text">
              <div class="name">{{ s.name }}</div>
              <div class="sub">{{ statusLabel(s.status) }}</div>
            </div>
          </div>
          <div v-if="!run?.steps?.length" class="empty-steps">无阶段信息</div>
        </div>

        <div class="details">
          <!-- Progress overview -->
          <div class="overview">
            <el-progress :percentage="run?.progress || 0" :stroke-width="12" :status="progressStatus"></el-progress>
            <div v-if="run?.currentOperation" class="op">当前：{{ run?.currentOperation }}</div>
            <!-- 失败时显示完整错误信息 -->
            <el-alert
              v-if="run?.status === 'failed' && errorMessage"
              type="error"
              title="错误详情"
              :closable="false"
              style="margin-top: 12px"
            >
              <pre class="error-detail">{{ errorMessage }}</pre>
            </el-alert>
          </div>

          <!-- Logs toolbar -->
          <div class="logs-toolbar">
            <el-radio-group v-model="levelFilter" size="small">
              <el-radio-button label="ALL">全部</el-radio-button>
              <el-radio-button label="ERROR">错误</el-radio-button>
              <el-radio-button label="WARN">警告</el-radio-button>
              <el-radio-button label="INFO">信息</el-radio-button>
            </el-radio-group>
            <el-input v-model="keyword" placeholder="搜索日志..." size="small" clearable style="width: 220px" />
          </div>

          <!-- 去除“长时间无新日志”告警 --><!---->

          <!-- Logs -->
          <div class="logs" ref="logsRef">
            <div
              v-for="(l, i) in filteredLogs"
              :key="i"
              :class="['log', l.level.toLowerCase()]"
            >
              <span class="ts">{{ formatTime(l.ts) }}</span>
              <span class="lv">{{ l.level }}</span>
              <span class="msg">{{ l.message }}</span>
            </div>
            <div v-if="filteredLogs.length===0" class="logs-empty">暂无日志</div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button v-if="canRetry" type="primary" @click="onRetry" :loading="retrying">重试</el-button>
        <el-button class="cloudera-btn secondary" @click="visible=false">关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { loadScanRun, loadMergeRun, loadArchiveRun, loadTestTableRun, type NormalizedTaskRun } from '@/api/taskRunAdapters'
import { tasksApi } from '@/api/tasks'

const props = defineProps<{
  modelValue: boolean
  type: 'scan' | 'merge' | 'archive' | 'test-table'
  scanTaskId?: string
  mergeTaskId?: number | string  // 支持测试表的字符串ID
}>()

const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const visible = computed({
  get: () => props.modelValue,
  set: v => emit('update:modelValue', v)
})

const run = ref<NormalizedTaskRun | null>(null)
const taskData = ref<any>(null)  // 保存原始任务数据用于获取error_message
const activeStepId = ref<string>('')
const levelFilter = ref<'ALL' | 'INFO' | 'WARN' | 'ERROR'>('ALL')
const keyword = ref('')
const logsRef = ref<HTMLElement>()
let poll: any = null

const dialogTitle = computed(() => {
  const base = props.type === 'scan' ? '扫描任务'
    : props.type === 'merge' ? '合并任务'
    : props.type === 'test-table' ? '测试表生成任务'
    : '归档任务'
  return `${base}执行详情`
})

const statusText = computed(() => {
  const s = (run.value?.status || '').toLowerCase()
  const map: Record<string, string> = {
    success: '成功',
    completed: '成功',
    running: '执行中',
    failed: '失败',
    pending: '等待中',
    queued: '排队中',
    cancelled: '已取消'
  }
  return map[s] || run.value?.status || '-'
})
const statusTagType = computed(() => {
  const s = (run.value?.status || '').toLowerCase()
  if (s === 'success' || s === 'completed') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'running') return 'primary'
  return 'info'
})
const progressStatus = computed(() => {
  const s = (run.value?.status || '').toLowerCase()
  if (s === 'failed') return 'exception'
  if (s === 'success' || s === 'completed') return 'success'
  return undefined
})

const shortId = computed(() => {
  const id = props.scanTaskId || String(props.mergeTaskId || '')
  if (!id) return '-'
  return id.length > 12 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id
})

const filteredLogs = computed(() => {
  // 固定为“最新在下”的正序（人类更习惯从上到下阅读，新日志追加到末尾）
  const base = (run.value?.logs || []).slice().sort((a, b) => {
    const ta = new Date(a.ts).getTime() || 0
    const tb = new Date(b.ts).getTime() || 0
    return ta - tb
  })
  return base.filter(l => {
    if (activeStepId.value && l.step_id && l.step_id !== activeStepId.value) return false
    if (levelFilter.value !== 'ALL' && l.level !== levelFilter.value) return false
    if (keyword.value && !l.message.toLowerCase().includes(keyword.value.toLowerCase())) return false
    return true
  })
})

const statusLabel = (s: string) => {
  switch (s) {
    case 'running': return '运行中'
    case 'success': return '已完成'
    case 'failed': return '失败'
    case 'skipped': return '跳过'
    case 'cancelled': return '已取消'
    default: return '待开始'
  }
}

const load = async () => {
  try {
  if (props.type === 'scan' && props.scanTaskId) {
    run.value = await loadScanRun(props.scanTaskId)
    taskData.value = await scanTasksApi.get(props.scanTaskId)
  } else if (props.type === 'merge' && props.mergeTaskId) {
    run.value = await loadMergeRun(props.mergeTaskId)
    taskData.value = await tasksApi.get(props.mergeTaskId)
  } else if (props.type === 'archive' && props.scanTaskId) {
    run.value = await loadArchiveRun({ taskId: props.scanTaskId })
    taskData.value = await scanTasksApi.get(props.scanTaskId)
  } else if (props.type === 'test-table' && props.mergeTaskId) {
    run.value = await loadTestTableRun(String(props.mergeTaskId))
    taskData.value = null  // 测试表任务暂不加载原始数据
  } else {
    run.value = null
    taskData.value = null
  }
    if (run.value && run.value.steps.length) {
      const logs = run.value.logs || []
      const normalize = (stepId?: string) => stepId || run.value.steps[0]?.id || ''
      const logStep = [...logs]
        .reverse()
        .map(l => normalize(l.step_id))
        .find(id => !!id)
      const hasLogsForActive = activeStepId.value
        ? logs.some(l => normalize(l.step_id) === activeStepId.value)
        : false
      const fallbackStep = run.value.steps.find(s => s.status === 'failed')
        || run.value.steps.find(s => s.status === 'running')
        || run.value.steps[0]
      if (!activeStepId.value || !hasLogsForActive) {
        activeStepId.value = logStep || (fallbackStep ? fallbackStep.id : '')
      }
    }
    await nextTick(); scrollBottom()
  } catch (e: any) {
    console.error('load run failed', e)
    ElMessage.error(e?.message || '加载失败')
  }
}

const startPoll = () => {
  stopPoll()
  if (props.type === 'scan') poll = setInterval(load, 2000)
  if (props.type === 'merge') poll = setInterval(load, 3000)
  if (props.type === 'archive') poll = setInterval(load, 2500)
  if (props.type === 'test-table') poll = setInterval(load, 2000)
}
const stopPoll = () => { if (poll) { clearInterval(poll); poll = null } }

watch(visible, v => { if (v) { load(); startPoll() } else { stopPoll() } })
watch(() => [props.scanTaskId, props.mergeTaskId, props.type], () => { if (visible.value) load() })

const copyId = async () => {
  const id = props.scanTaskId || String(props.mergeTaskId || '')
  try { await navigator.clipboard.writeText(id); ElMessage.success('已复制任务ID') } catch {}
}
const exportAllLogs = () => {
  const text = (run.value?.logs || []).map(l => `${l.ts} [${l.level}] ${l.message}`).join('\n')
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = 'task-logs.txt'; a.click(); URL.revokeObjectURL(url)
}
const scrollBottom = () => { if (logsRef.value) logsRef.value.scrollTop = logsRef.value.scrollHeight }
const scrollTop = () => { if (logsRef.value) logsRef.value.scrollTop = 0 }

const formatTime = (t?: string) => t ? dayjs(t).format('YYYY-MM-DD HH:mm:ss') : '-'

// 获取完整错误信息
const errorMessage = computed(() => {
  if (!taskData.value || run.value?.status !== 'failed') return ''
  return taskData.value.error_message || ''
})

onMounted(() => { if (visible.value) { load(); startPoll() } })
watch(filteredLogs, async () => { await nextTick(); scrollBottom() })

// 重试：当前支持合并任务。失败时显示“重试”按钮
const canRetry = computed(() => {
  if (!(props.type === 'merge' && !!props.mergeTaskId)) return false
  const s = (run.value?.status || '').toLowerCase()
  return s === 'failed' || s === 'cancelled'
})
const retrying = ref(false)
const onRetry = async () => {
  if (!props.mergeTaskId) return
  try {
    retrying.value = true
    await tasksApi.retry(props.mergeTaskId)
    ElMessage.success('已触发重试')
    await load()
    startPoll()
  } catch (e: any) {
    console.error('retry failed', e)
    ElMessage.error(e?.message || '重试失败')
  } finally {
    retrying.value = false
  }
}

// 取消运行中的任务（合并）
const isRunning = computed(() => (run.value?.status || '').toLowerCase() === 'running')
const canCancel = computed(() => props.type === 'merge' && !!props.mergeTaskId && isRunning.value)
const onCancel = async () => {
  if (!props.mergeTaskId) return
  try {
    await tasksApi.cancel(props.mergeTaskId)
    ElMessage.success('已取消任务')
    await load()
  } catch (e: any) {
    console.error('cancel failed', e)
    ElMessage.error(e?.message || '取消失败')
  }
}

// Watchdog：统计距离最近一条日志的时间，超过阈值给用户提示
const lastLogAt = computed(() => {
  const arr = run.value?.logs || []
  if (arr.length === 0) return run.value?.startedAt ? dayjs(run.value?.startedAt).valueOf() : 0
  const last = arr[arr.length - 1]
  return dayjs(last.ts || run.value?.startedAt || Date.now()).valueOf()
})
const staleSeconds = computed(() => {
  const last = lastLogAt.value
  if (!last) return 0
  const diff = Math.max(0, Math.floor((Date.now() - last) / 1000))
  return diff
})
const humanizeDuration = (sec: number) => {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  if (m <= 0) return `${s}s`
  return `${m}m${s.toString().padStart(2, '0')}s`
}
const forceRefresh = async () => { await load() }
</script>

<style scoped>
.task-run {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-height: calc(100vh - 200px);
  height: calc(100vh - 200px);
  overflow: hidden;
}
.header-summary { display: flex; justify-content: space-between; align-items: center; }
.header-summary .meta { display: flex; gap: 12px; align-items: center; }
.kv { color: #606266; font-size: 12px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 12px; color: #303133 }
.ops { display: flex; gap: 8px; }
.body { display: grid; grid-template-columns: 240px 1fr; gap: 16px; flex: 1 1 auto; min-height: 0; overflow: hidden; }
.steps { border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px; background: #fff; overflow: auto; }
.step { display: flex; gap: 8px; align-items: center; padding: 10px 8px; border-radius: 6px; cursor: pointer; }
.step:hover, .step.active { background: #f5f7fa; }
.step .dot { width: 10px; height: 10px; border-radius: 50%; background: #c0c4cc; }
.step.success .dot { background: #67c23a; }
.step.failed .dot { background: #f56c6c; }
.step.running .dot { background: #409eff; }
.step.cancelled .dot { background: #909399; }
.step .text .name { font-weight: 600; color: #303133; }
.step .text .sub { font-size: 12px; color: #909399; }
.empty-steps { color: #909399; font-size: 12px; padding: 8px; }
.details { display: flex; flex-direction: column; gap: 12px; min-height: 0; }
.overview { display: flex; flex-direction: column; gap: 6px; padding: 8px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }
.overview .op { color: #606266; font-size: 12px; }
.logs-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.stalled-banner { margin: 8px 0; }
.orders { display: inline-flex; align-items: center; gap: 8px; }
.logs { flex: 1 1 auto; min-height: 200px; overflow: auto; font-family: ui-monospace, monospace; background: #1f2937; color: #fff; border-radius: 8px; padding: 12px; }
.log { display: grid; grid-template-columns: 160px 60px 1fr; gap: 8px; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.08) }
.log:last-child { border-bottom: none }
.log .ts { color: #cbd5e1; font-size: 12px }
.log .lv { color: #93c5fd; font-size: 12px }
.log.warn .lv, .log.WARN .lv { color: #fbbf24 }
.log.error .lv, .log.ERROR .lv { color: #f87171 }
.log .msg {
  white-space: pre-wrap;
  word-break: break-all;
  overflow-wrap: anywhere;
}
.logs-empty { color: #cbd5e1; text-align: center; padding: 12px; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 8px; }

/* 错误详情样式 */
.error-detail {
  margin: 0;
  padding: 12px;
  background: #2c2c2c;
  color: #f56c6c;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
