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

  // Group logs by phase as steps
  const phaseOrder: string[] = []
  const phaseMap: Record<string, TaskStep> = {}
  for (const l of logs || []) {
    const phase = l.phase || '执行'
    if (!phaseMap[phase]) {
      phaseMap[phase] = { id: phase, name: phase, status: 'running' }
      phaseOrder.push(phase)
    }
    if (String(l.log_level || '').toUpperCase() === 'ERROR') {
      phaseMap[phase].status = 'failed'
    }
  }
  // Finalize status
  const finalStatus = task.status || 'running'
  for (const p of phaseOrder) {
    if (finalStatus === 'success' && phaseMap[p].status !== 'failed') {
      phaseMap[p].status = 'success'
    } else if (finalStatus === 'failed' && phaseMap[p].status !== 'failed') {
      phaseMap[p].status = 'failed'
    }
  }
  const steps = phaseOrder.map(p => phaseMap[p])

  const normLogs: TaskLogItem[] = (logs || []).map(l => ({
    ts: String(l.timestamp || ''),
    level: levelMap(l.log_level),
    source: 'merge',
    message: l.message || '',
    step_id: l.phase || undefined
  }))

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
