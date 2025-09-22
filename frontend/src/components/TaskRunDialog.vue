<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="960px"
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
        <el-button class="cloudera-btn secondary" @click="visible=false">关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { loadScanRun, loadMergeRun, loadArchiveRun, type NormalizedTaskRun } from '@/api/taskRunAdapters'

const props = defineProps<{
  modelValue: boolean
  type: 'scan' | 'merge' | 'archive'
  scanTaskId?: string
  mergeTaskId?: number
}>()

const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const visible = computed({
  get: () => props.modelValue,
  set: v => emit('update:modelValue', v)
})

const run = ref<NormalizedTaskRun | null>(null)
const activeStepId = ref<string>('')
const levelFilter = ref<'ALL' | 'INFO' | 'WARN' | 'ERROR'>('ALL')
const keyword = ref('')
const logsRef = ref<HTMLElement>()
let poll: any = null

const dialogTitle = computed(() => {
  const base = props.type === 'scan' ? '扫描任务' : props.type === 'merge' ? '合并任务' : '归档任务'
  return `${base}执行详情`
})

const statusText = computed(() => run.value?.status || '-')
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
  } else if (props.type === 'merge' && props.mergeTaskId) {
    run.value = await loadMergeRun(props.mergeTaskId)
  } else if (props.type === 'archive' && props.scanTaskId) {
    run.value = await loadArchiveRun({ taskId: props.scanTaskId })
  } else {
    run.value = null
  }
    if (run.value && !activeStepId.value && run.value.steps.length) {
      activeStepId.value = run.value.steps[0].id
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

onMounted(() => { if (visible.value) { load(); startPoll() } })
watch(filteredLogs, async () => { await nextTick(); scrollBottom() })
</script>

<style scoped>
.task-run { display: flex; flex-direction: column; gap: 12px; }
.header-summary { display: flex; justify-content: space-between; align-items: center; }
.header-summary .meta { display: flex; gap: 12px; align-items: center; }
.kv { color: #606266; font-size: 12px; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 12px; color: #303133 }
.ops { display: flex; gap: 8px; }
.body { display: grid; grid-template-columns: 240px 1fr; gap: 16px; min-height: 420px; }
.steps { border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px; background: #fff; }
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
.details { display: flex; flex-direction: column; gap: 12px; }
.overview { display: flex; flex-direction: column; gap: 6px; padding: 8px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }
.overview .op { color: #606266; font-size: 12px; }
.logs-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.orders { display: inline-flex; align-items: center; gap: 8px; }
.logs { height: 300px; overflow: auto; font-family: ui-monospace, monospace; background: #1f2937; color: #fff; border-radius: 8px; padding: 12px; }
.log { display: grid; grid-template-columns: 160px 60px 1fr; gap: 8px; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.08) }
.log:last-child { border-bottom: none }
.log .ts { color: #cbd5e1; font-size: 12px }
.log .lv { color: #93c5fd; font-size: 12px }
.log.warn .lv, .log.WARN .lv { color: #fbbf24 }
.log.error .lv, .log.ERROR .lv { color: #f87171 }
.log .msg { white-space: pre-wrap; }
.logs-empty { color: #cbd5e1; text-align: center; padding: 12px; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 8px; }
</style>
