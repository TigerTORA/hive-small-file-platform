import type { MergeTask } from '@/api/tasks'

/**
 * 标准化任务状态
 */
export function normalizeStatus(status: string): string {
  return status === 'completed' ? 'success' : status
}

/**
 * 获取状态类型（用于Element Plus Tag组件）
 */
export function getStatusType(status: string): string {
  const statusMap: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return statusMap[status] || 'info'
}

/**
 * 获取状态文本
 */
export function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    pending: '排队中',
    running: '正在执行',
    success: '已成功',
    failed: '失败',
    cancelled: '已取消'
  }
  return statusMap[status] || status
}

/**
 * 获取合并策略名称
 */
export function getStrategyName(strategy: string): string {
  const strategyMap: Record<string, string> = {
    safe_merge: '安全合并',
    concatenate: '文件合并',
    insert_overwrite: '重写插入'
  }
  return strategyMap[strategy] || strategy
}

/**
 * 获取执行阶段文本
 */
export function getExecutionPhase(row: MergeTask): string {
  if (row.status !== 'running') return ''

  if (row.execution_phase) {
    const phaseMap: Record<string, string> = {
      initialization: '初始化中',
      connection_test: '连接测试',
      pre_validation: '预验证',
      file_analysis: '文件分析',
      temp_table_creation: '创建临时表',
      data_validation: '数据验证',
      atomic_swap: '原子切换',
      post_validation: '后验证',
      cleanup: '清理中',
      completion: '完成中'
    }
    return phaseMap[row.execution_phase] || row.execution_phase
  }

  return '执行中'
}

/**
 * 获取任务进度百分比
 */
export function getTaskProgress(row: MergeTask): number {
  if (row.status === 'success') return 100
  if (row.status === 'failed') return 0

  if (row.execution_phase) {
    const progressMap: Record<string, number> = {
      initialization: 5,
      connection_test: 10,
      pre_validation: 15,
      file_analysis: 25,
      temp_table_creation: 45,
      data_validation: 65,
      atomic_swap: 80,
      post_validation: 90,
      cleanup: 95,
      completion: 98
    }
    return progressMap[row.execution_phase] || 50
  }

  if (row.progress_percentage !== undefined && row.progress_percentage !== null) {
    return row.progress_percentage
  }

  return 50
}

/**
 * 获取进度文本
 */
export function getProgressText(row: MergeTask): string {
  if (row.status !== 'running') return ''

  const phase = getExecutionPhase(row)
  const progress = getTaskProgress(row)

  if (row.estimated_remaining_time) {
    const duration = formatDuration(row.estimated_remaining_time)
    return `${phase} - ${progress}% (预计剩余 ${duration})`
  }

  if (row.processed_files_count && row.total_files_count) {
    return `${phase} - ${row.processed_files_count}/${row.total_files_count} 文件`
  }

  return `${phase} - ${progress}%`
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}秒`
  if (seconds < 3600) return `${Math.round(seconds / 60)}分钟`
  return `${Math.round(seconds / 3600)}小时`
}

/**
 * 归档类型标签
 */
export function archiveTypeLabel(sub: string): string {
  if (sub === 'archive-table') return '表归档'
  if (sub === 'restore-table') return '表恢复'
  if (sub === 'archive-table-policy') return '策略归档'
  if (sub === 'restore-table-policy') return '策略恢复'
  if (sub && sub.startsWith('archive')) return '归档'
  return '扫描'
}

/**
 * 归档类型Tag颜色
 */
export function archiveTypeTag(sub: string): string {
  if (sub === 'archive-table') return 'warning'
  if (sub === 'restore-table') return 'success'
  if (sub === 'archive-table-policy') return 'primary'
  if (sub === 'restore-table-policy') return 'success'
  return 'info'
}

/**
 * 解析结构化日志消息
 */
export function parseStructured(msg: string): { code?: string; ctx?: Record<string, string> } {
  const m = msg.match(/\]\s*(\w+)\s+/)
  const code = m ? m[1] : undefined
  const ctx: Record<string, string> = {}
  const kvRe = /(\w+)=([^\s]+)/g
  let mm
  while ((mm = kvRe.exec(msg)) !== null) {
    ctx[mm[1]] = mm[2]
  }
  return { code, ctx }
}

/**
 * 复制ID到剪贴板
 */
export async function copyId(id: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(id)
  } catch (error) {
    // 忽略复制失败
  }
}
