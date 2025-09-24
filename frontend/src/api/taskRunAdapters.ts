import api from './index'
import { scanTasksApi } from './scanTasks'
import { tasksApi } from './tasks'

export type TaskType = 'scan' | 'merge' | 'archive'

export interface TaskStep {
  id: string
  name: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped' | 'cancelled'
  start_at?: string
  end_at?: string
  duration_ms?: number
  attempts?: number
  metrics?: Record<string, any>
}

export interface TaskLogItem {
  ts: string
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG'
  source?: string
  message: string
  step_id?: string
}

export interface NormalizedTaskRun {
  title: string
  status: string
  progress?: number
  currentOperation?: string
  startedAt?: string
  finishedAt?: string
  steps: TaskStep[]
  logs: TaskLogItem[]
}

const MERGE_PHASE_LABELS: Record<string, string> = {
  initialization: '初始化',
  connection_test: '连接测试',
  pre_validation: '执行前校验',
  file_analysis: '文件分析',
  temp_table_creation: '临时表创建',
  data_validation: '数据校验',
  atomic_swap: '原子表切换',
  post_validation: '执行后校验',
  cleanup: '清理',
  rollback: '回滚',
  completion: '完成',
  execution: '执行',
  monitor: '监控',
  maintenance: '维护'
}

const friendlyPhaseName = (rawName: string): string => {
  const key = (rawName || '').trim().toLowerCase()
  if (!key) return '运行日志'
  const mapped = MERGE_PHASE_LABELS[key]
  if (mapped) return mapped
  return key
    .split('_')
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

// Utilities
const levelMap = (s: string | undefined): TaskLogItem['level'] => {
  const up = (s || '').toUpperCase()
  return up === 'WARN' ? 'WARN' : up === 'ERROR' ? 'ERROR' : up === 'DEBUG' ? 'DEBUG' : 'INFO'
}

// Adapters
export async function loadScanRun(taskId: string): Promise<NormalizedTaskRun> {
  const task = await scanTasksApi.get(taskId)
  let logs: any[] = []
  try { logs = await scanTasksApi.getLogs(taskId) } catch {}

  // Basic 3-step model for scanning
  // 1) 初始化连接 2) 扫描数据 3) 汇总统计
  const status = task.status || 'running'
  const steps: TaskStep[] = [
    { id: 'init', name: '初始化连接', status: 'success' as const },
    { id: 'scan', name: '扫描数据', status: 'running' as const },
    { id: 'summary', name: '汇总统计', status: 'pending' as const }
  ]

  if (status === 'completed') {
    steps[1].status = 'success'
    steps[2].status = 'success'
  } else if (status === 'failed') {
    steps[1].status = 'failed'
    steps[2].status = 'failed'
  } else {
    steps[1].status = 'running'
  }

  // Try to refine step status from logs keywords
  const err = (logs || []).some(l => (l.level || '').toUpperCase() === 'ERROR')
  if (err) steps[1].status = 'failed'

  const normLogs: TaskLogItem[] = (logs || []).map(l => ({
    ts: String(l.timestamp || ''),
    level: levelMap(l.level),
    source: l.database_name || l.table_name ? 'scanner' : undefined,
    message: l.message || ''
  }))

  return {
    title: task.task_name || '全库扫描',
    status,
    progress: task.progress_percentage || 0,
    currentOperation: task.current_item || '',
    startedAt: task.start_time,
    finishedAt: task.end_time,
    steps,
    logs: normLogs
  }
}

export async function loadMergeRun(taskId: number): Promise<NormalizedTaskRun> {
  const task = await tasksApi.get(taskId)
  let logs: any[] = []
  try { logs = await tasksApi.getLogs(taskId) } catch {}

  // Group logs by phase and infer per-phase status from start/end messages
  const phaseOrder: string[] = []
  const phaseData: Record<string, { step: TaskStep; started?: boolean; finished?: boolean }> = {}
  const up = (s: string | undefined) => String(s || '').toUpperCase()
  const contains = (msg: string, kw: string) => msg.indexOf(kw) >= 0
  const addPhase = (name: string) => {
    if (!phaseData[name]) {
      phaseData[name] = {
        step: {
          id: name,
          name: friendlyPhaseName(name),
          status: 'pending'
        }
      }
      phaseOrder.push(name)
    }
  }
  for (const l of logs || []) {
    const phase = l.phase || '执行'
    const msg: string = String(l.message || '')
    addPhase(phase)
    const data = phaseData[phase]
    // Start marker
    if (contains(msg, '开始阶段') || contains(msg, '开始')) {
      data.started = true
      if (data.step.status !== 'failed') data.step.status = 'running'
    }
    // End markers
    if (contains(msg, '阶段完成') || contains(msg, '完成')) {
      data.finished = true
      if (data.step.status !== 'failed') data.step.status = 'success'
    }
    // 仅当明确出现“阶段失败”时标记失败；普通 ERROR 日志不直接判定失败
    if (contains(msg, '阶段失败')) {
      data.finished = true
      data.step.status = 'failed'
    }
    // 记录是否出现过 ERROR（用于最终失败推断，但不立刻置失败）
    if ((logs && up(l.log_level) === 'ERROR')) (data as any).sawError = true
  }
  // If a later phase has started, mark earlier, not failed ones as success
  let seenRunning = false
  for (let i = phaseOrder.length - 1; i >= 0; i--) {
    const key = phaseOrder[i]
    const d = phaseData[key]
    if (!d.started && !d.finished) continue
    if (!seenRunning && d.step.status === 'running') {
      seenRunning = true
    } else if (seenRunning && d.step.status === 'running') {
      d.step.status = 'success'
    }
  }
  // 若任务整体失败，最后一个已开始的阶段标记失败；否则保持运行/成功
  const finalStatus = (task.status || '').toLowerCase()
  if (finalStatus === 'failed') {
    for (let i = phaseOrder.length - 1; i >= 0; i--) {
      const key = phaseOrder[i]
      const d = phaseData[key]
      if (d.started) { d.step.status = 'failed'; break }
    }
  }
  const steps = phaseOrder.map(p => phaseData[p].step)

  const startedAtTs = task.started_time ? new Date(task.started_time).getTime() : undefined
  const normLogs: TaskLogItem[] = (logs || [])
    .map(l => ({
      ts: String(l.timestamp || ''),
      level: levelMap(l.log_level),
      source: 'merge',
      message: l.message || '',
      step_id: l.phase || undefined
    }))
    .filter(item => {
      if (!startedAtTs) return true
      const ts = new Date(item.ts).getTime()
      if (Number.isNaN(ts)) return true
      return ts >= startedAtTs - 1000 // allow minor clock skew
    })

  return {
    title: task.task_name || `${task.database_name}.${task.table_name}`,
    status: task.status,
    progress: task.progress_percentage || 0,
    currentOperation: task.current_operation || '',
    startedAt: task.started_time ? String(task.started_time) : undefined,
    finishedAt: task.completed_time ? String(task.completed_time) : undefined,
    steps,
    logs: normLogs
  }
}

export async function loadArchiveRun(payload: { taskId: string }): Promise<NormalizedTaskRun> {
  // 归档任务接入 ScanTask 模型（task_type = 'archive-*'），使用相同日志端点
  const task = await scanTasksApi.get(payload.taskId)
  let logs: any[] = []
  try { logs = await scanTasksApi.getLogs(payload.taskId) } catch {}

  // 简约的三阶段：准备/执行/完成
  const status = task.status || 'running'
  const steps: TaskStep[] = [
    { id: 'prepare', name: '准备', status: 'success' as const },
    { id: 'archive', name: '归档执行', status: 'running' as const },
    { id: 'finalize', name: '完成', status: 'pending' as const }
  ]

  if (status === 'completed') {
    steps[1].status = 'success'; steps[2].status = 'success'
  } else if (status === 'failed') {
    steps[1].status = 'failed'; steps[2].status = 'failed'
  }

  const hasError = (logs || []).some(l => (l.level || '').toUpperCase() === 'ERROR')
  if (hasError) steps[1].status = 'failed'

  const normLogs: TaskLogItem[] = (logs || []).map(l => ({
    ts: String(l.timestamp || ''),
    level: levelMap(l.level),
    source: 'archive',
    message: l.message || ''
  }))

  return {
    title: task.task_name || '归档任务',
    status,
    progress: task.progress_percentage || 0,
    currentOperation: task.current_item || '',
    startedAt: task.start_time,
    finishedAt: task.end_time,
    steps,
    logs: normLogs
  }
}
