import { ref, computed } from 'vue'
import type { Ref, ComputedRef } from 'vue'
import type { MergeTask } from '@/api/tasks'
import type { ScanTask } from '@/api/scanTasks'
import { normalizeStatus } from '@/utils/tasks/taskHelpers'
import { getTaskProgress } from '@/utils/tasks/taskHelpers'

/**
 * 任务筛选器状态和逻辑
 */
export function useTaskFilters(
  tasks: Ref<MergeTask[]>,
  testTableTasks: Ref<any[]>,
  scanTasks: Ref<ScanTask[]>,
  archiveTasks: Ref<any[]>
) {
  // 筛选器状态
  const globalSearch = ref('')
  const taskSearchText = ref('')
  const selectedStatuses = ref<Set<string>>(new Set())
  const selectedTypes = ref<Set<string>>(new Set())
  const selectedArchiveSubtypes = ref<Set<string>>(new Set())

  // 筛选器选项
  const statusOptions = [
    { label: '失败', value: 'failed' },
    { label: '已成功', value: 'success' },
    { label: '正在执行', value: 'running' },
    { label: '已取消', value: 'cancelled' },
    { label: '排队中', value: 'pending' }
  ]

  const typeOptions = [
    { label: '合并任务', value: 'merge' },
    { label: '扫描任务', value: 'scan' },
    { label: '归档任务', value: 'archive' },
    { label: '测试表生成', value: 'test-table-generation' }
  ]

  const archiveSubtypeOptions = [
    { label: '表归档', value: 'archive-table' },
    { label: '表恢复', value: 'restore-table' },
    { label: '策略归档', value: 'archive-table-policy' },
    { label: '策略恢复', value: 'restore-table-policy' }
  ]

  // 切换筛选器
  const toggleStatus = (s: string) => {
    const set = selectedStatuses.value
    set.has(s) ? set.delete(s) : set.add(s)
  }

  const toggleType = (t: string) => {
    const set = selectedTypes.value
    set.has(t) ? set.delete(t) : set.add(t)
  }

  const toggleArchiveSubtype = (v: string) => {
    const set = selectedArchiveSubtypes.value
    set.has(v) ? set.delete(v) : set.add(v)
  }

  const resetFilters = () => {
    selectedStatuses.value.clear()
    selectedTypes.value.clear()
    selectedArchiveSubtypes.value.clear()
    globalSearch.value = ''
    taskSearchText.value = ''
  }

  // 搜索匹配
  const matchSearch = (text: string) => {
    const q = (globalSearch.value || taskSearchText.value || '').trim().toLowerCase()
    if (!q) return true
    return (text || '').toLowerCase().includes(q)
  }

  // 状态统计
  const statusCounts = computed<Record<string, number>>(() => {
    const map: Record<string, number> = {}
    for (const r of tasks.value) {
      const s = normalizeStatus(r.status)
      map[s] = (map[s] || 0) + 1
    }
    for (const r of scanTasks.value) {
      const s = normalizeStatus(r.status)
      map[s] = (map[s] || 0) + 1
    }
    for (const r of archiveTasks.value) {
      const s = 'success'
      map[s] = (map[s] || 0) + 1
    }
    for (const r of testTableTasks.value) {
      const s = normalizeStatus(r.status)
      map[s] = (map[s] || 0) + 1
    }
    return map
  })

  const typeCounts = computed<Record<string, number>>(() => ({
    merge: tasks.value.length,
    scan: scanTasks.value.length,
    archive: archiveTasks.value.length,
    'test-table-generation': testTableTasks.value.length
  }))

  const archiveSubtypeCounts = computed<Record<string, number>>(() => {
    const m: Record<string, number> = {}
    for (const r of scanTasks.value) {
      const sub = String((r as any).task_type)
      if (sub.startsWith('archive') || sub.startsWith('restore')) m[sub] = (m[sub] || 0) + 1
    }
    return m
  })

  // 过滤后的任务
  const filteredTasks = computed(() => {
    if (selectedTypes.value.size && !selectedTypes.value.has('merge')) return []
    return tasks.value.filter(task => {
      const s = normalizeStatus(task.status)
      if (selectedStatuses.value.size && !selectedStatuses.value.has(s)) return false
      const text = `${task.task_name} ${task.database_name}.${task.table_name}`
      return matchSearch(text)
    })
  })

  const filteredTestTableTasks = computed(() => {
    if (selectedTypes.value.size && !selectedTypes.value.has('test-table-generation')) return []
    return testTableTasks.value.filter(task => {
      const s = normalizeStatus(task.status)
      if (selectedStatuses.value.size && !selectedStatuses.value.has(s)) return false
      const text = `${task.task_name || ''} ${task.database_name || ''}.${task.table_name || ''}`
      return matchSearch(text)
    })
  })

  const filteredScanTasks = computed(() => {
    if (selectedTypes.value.size && !selectedTypes.value.has('scan')) return []
    return scanTasks.value.filter(task => {
      const s = normalizeStatus(task.status)
      if (selectedStatuses.value.size && !selectedStatuses.value.has(s)) return false

      const tt = String((task as any).task_type || '')
      if (tt.startsWith('archive')) {
        if (selectedArchiveSubtypes.value.size && !selectedArchiveSubtypes.value.has(tt)) return false
      } else {
        if (selectedArchiveSubtypes.value.size) return false
      }

      const text = `${task.task_name || ''}`
      return matchSearch(text)
    })
  })

  // 统一的任务列表
  const filteredAllTasks = computed(() => {
    const mergeRows = filteredTasks.value.map(row => ({
      type: 'merge',
      raw: row,
      task_name: row.task_name,
      database_name: row.database_name,
      table_name: row.table_name,
      status: row.status,
      progress: getTaskProgress(row),
      start_time: row.created_time,
      last_update: (row as any).updated_time || row.created_time
    }))

    const testTableRows = filteredTestTableTasks.value.map(row => ({
      type: 'test-table-generation',
      raw: row,
      id: row.id,
      task_name: row.task_name,
      database_name: row.database_name,
      table_name: row.table_name,
      status: normalizeStatus(row.status),
      progress: row.progress_percentage ?? row.progress ?? 0,
      start_time: row.created_time,
      last_update: row.completed_time || row.started_time || row.created_time
    }))

    const scanRows = filteredScanTasks.value.map(r => ({
      type:
        (r as any).task_type &&
        (String((r as any).task_type).startsWith('archive') ||
          String((r as any).task_type).startsWith('restore'))
          ? 'archive'
          : 'scan',
      raw: r,
      task_name: r.task_name || '扫描任务',
      database_name: null as any,
      table_name: null as any,
      status: normalizeStatus(r.status),
      progress: r.progress_percentage || 0,
      start_time: r.start_time,
      last_update: (r as any).last_update || r.end_time || r.start_time,
      task_id: r.task_id,
      subtype: (r as any).task_type
    }))

    const archiveRows =
      selectedTypes.value.size && !selectedTypes.value.has('archive')
        ? []
        : archiveTasks.value.map(r => ({
            type: 'archive',
            raw: r,
            task_name: r.task_name || `归档 ${r.database_name}.${r.table_name}`,
            database_name: r.database_name,
            table_name: r.table_name,
            status: 'success',
            progress: 100,
            start_time: r.archived_at,
            last_update: r.archived_at
          }))

    return [...mergeRows, ...testTableRows, ...scanRows, ...archiveRows].sort(
      (a, b) =>
        new Date(b.last_update || b.start_time).getTime() -
        new Date(a.last_update || a.start_time).getTime()
    )
  })

  return {
    // 状态
    globalSearch,
    taskSearchText,
    selectedStatuses,
    selectedTypes,
    selectedArchiveSubtypes,

    // 选项
    statusOptions,
    typeOptions,
    archiveSubtypeOptions,

    // 统计
    statusCounts,
    typeCounts,
    archiveSubtypeCounts,

    // 过滤结果
    filteredTasks,
    filteredTestTableTasks,
    filteredScanTasks,
    filteredAllTasks,

    // 方法
    toggleStatus,
    toggleType,
    toggleArchiveSubtype,
    resetFilters
  }
}
