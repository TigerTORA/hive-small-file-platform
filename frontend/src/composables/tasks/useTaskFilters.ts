import { computed, ref } from 'vue'
import type { Ref } from 'vue'
import type { MergeTask } from '@/api/tasks'
import type { ScanTask } from '@/api/scanTasks'
import type { Cluster } from '@/api/clusters'
import {
  normalizeStatus,
  getTaskProgress,
  getStatusText,
  archiveTypeLabel
} from '@/utils/tasks/taskHelpers'

interface TaskRow {
  id: string | number
  type: 'merge' | 'scan' | 'archive' | 'test-table-generation'
  subtype?: string
  raw: any
  task_name: string
  cluster_id: number | null
  cluster_name: string
  database_name?: string | null
  table_name?: string | null
  status: string
  progress: number
  start_time?: string
  last_update?: string
  task_id?: string
  search_text: string
  files_before?: number | null
  files_after?: number | null
  size_saved?: number | null
}

export function useTaskFilters(
  tasks: Ref<MergeTask[]>,
  testTableTasks: Ref<any[]>,
  scanTasks: Ref<ScanTask[]>,
  archiveTasks: Ref<any[]>,
  clusters: Ref<Cluster[]>
) {
  const globalSearch = ref('')
  const selectedStatuses = ref<Set<string>>(new Set())
  const selectedTypes = ref<Set<string>>(new Set())
  const selectedArchiveSubtypes = ref<Set<string>>(new Set())
  const selectedCluster = ref<number | 'all'>('all')
  const selectedTimeframe = ref<'24h' | '7d' | '30d' | 'all'>('all')

  const timeframeOptions = [
    { label: '近24小时', value: '24h' as const },
    { label: '近7天', value: '7d' as const },
    { label: '近30天', value: '30d' as const },
    { label: '全部时间', value: 'all' as const }
  ]

  const clusterOptions = computed(() => [
    { label: '全部集群', value: 'all' as const },
    ...clusters.value.map(cluster => ({
      label: cluster.name,
      value: cluster.id as number
    }))
  ])

  const clusterNameMap = computed<Record<number, string>>(() => {
    const map: Record<number, string> = {}
    for (const cluster of clusters.value) {
      map[cluster.id] = cluster.name
    }
    return map
  })

  const baseRows = computed<TaskRow[]>(() => {
    const rows: TaskRow[] = []

    for (const row of tasks.value) {
      const status = normalizeStatus(row.status)
      const clusterId = row.cluster_id ?? null
      const clusterName = clusterId ? clusterNameMap.value[clusterId] || `#${clusterId}` : '未知集群'
      const lastUpdate =
        (row as any).updated_time || row.completed_time || row.started_time || row.created_time

      rows.push({
        id: row.id,
        type: 'merge',
        raw: row,
        task_name: row.task_name,
        cluster_id: clusterId,
        cluster_name: clusterName,
        database_name: row.database_name,
        table_name: row.table_name,
        status,
        progress: getTaskProgress(row),
        start_time: row.created_time,
        last_update: lastUpdate,
        task_id: String(row.id),
        files_before: row.files_before ?? null,
        files_after: row.files_after ?? null,
        size_saved: row.size_saved ?? null,
        search_text: `${row.task_name || ''} ${clusterName} ${row.database_name || ''} ${row.table_name || ''}`.toLowerCase()
      })
    }

    for (const row of testTableTasks.value) {
      const status = normalizeStatus(row.status)
      const clusterId = row.cluster_id ?? null
      const clusterName = clusterId ? clusterNameMap.value[clusterId] || `#${clusterId}` : '未知集群'
      const lastUpdate = row.completed_time || row.started_time || row.created_time

      rows.push({
        id: row.id,
        type: 'test-table-generation',
        raw: row,
        task_name: row.task_name,
        cluster_id: clusterId,
        cluster_name: clusterName,
        database_name: row.database_name,
        table_name: row.table_name,
        status,
        progress: row.progress_percentage ?? row.progress ?? 0,
        start_time: row.created_time,
        last_update: lastUpdate,
        task_id: String(row.id),
        files_before: null,
        files_after: null,
        size_saved: null,
        search_text: `${row.task_name || ''} ${clusterName} ${row.database_name || ''} ${row.table_name || ''}`.toLowerCase()
      })
    }

    for (const row of scanTasks.value) {
      const status = normalizeStatus(row.status)
      const clusterId = row.cluster_id ?? null
      const clusterName = clusterId ? clusterNameMap.value[clusterId] || `#${clusterId}` : '未知集群'
      const subtype = String((row as any).task_type || '')
      const isArchiveSubtype = subtype.startsWith('archive') || subtype.startsWith('restore')
      const type = isArchiveSubtype ? 'archive' : 'scan'
      const lastUpdate = (row as any).last_update || row.end_time || row.start_time

      rows.push({
        id: row.task_id,
        type,
        subtype: isArchiveSubtype ? subtype : undefined,
        raw: row,
        task_name: row.task_name || (isArchiveSubtype ? archiveTypeLabel(subtype) : '扫描任务'),
        cluster_id: clusterId,
        cluster_name: clusterName,
        database_name: null,
        table_name: null,
        status,
        progress: row.progress_percentage || 0,
        start_time: row.start_time,
        last_update: lastUpdate,
        task_id: row.task_id,
        files_before: null,
        files_after: null,
        size_saved: null,
        search_text: `${row.task_name || ''} ${clusterName}`.toLowerCase()
      })
    }

    for (const row of archiveTasks.value) {
      const clusterId = row.cluster_id ?? null
      const clusterName = clusterId ? clusterNameMap.value[clusterId] || `#${clusterId}` : '未知集群'

      rows.push({
        id: `${row.cluster_id}-${row.database_name}-${row.table_name}`,
        type: 'archive',
        subtype: 'archive-history',
        raw: row,
        task_name: row.task_name || `归档 ${row.database_name}.${row.table_name}`,
        cluster_id: clusterId,
        cluster_name: clusterName,
        database_name: row.database_name,
        table_name: row.table_name,
        status: 'success',
        progress: 100,
        start_time: row.archived_at,
        last_update: row.archived_at,
        task_id: undefined,
        files_before: null,
        files_after: null,
        size_saved: null,
        search_text: `${row.task_name || ''} ${clusterName} ${row.database_name || ''} ${row.table_name || ''}`.toLowerCase()
      })
    }

    return rows
  })

  const statusCounts = computed<Record<string, number>>(() => {
    const counts: Record<string, number> = {}
    for (const row of baseRows.value) {
      counts[row.status] = (counts[row.status] || 0) + 1
    }
    return counts
  })

  const typeCounts = computed<Record<string, number>>(() => {
    const counts: Record<string, number> = {}
    for (const row of baseRows.value) {
      counts[row.type] = (counts[row.type] || 0) + 1
    }
    return counts
  })

  const archiveSubtypeCounts = computed<Record<string, number>>(() => {
    const counts: Record<string, number> = {}
    for (const row of baseRows.value) {
      if (row.type === 'archive' && row.subtype) {
        counts[row.subtype] = (counts[row.subtype] || 0) + 1
      }
    }
    return counts
  })

  const statusOrder = ['running', 'pending', 'success', 'failed', 'cancelled']

  const statusOptions = computed(() =>
    statusOrder
      .filter(value => statusCounts.value[value])
      .map(value => ({ value, label: getStatusText(value) }))
  )

  const typeOptions = computed(() =>
    [
      { value: 'merge', label: '合并任务' },
      { value: 'scan', label: '扫描任务' },
      { value: 'archive', label: '归档任务' },
      { value: 'test-table-generation', label: '测试表生成' }
    ].filter(option => typeCounts.value[option.value] > 0)
  )

  const archiveSubtypeOptions = computed(() =>
    Object.keys(archiveSubtypeCounts.value).map(value => ({
      value,
      label: archiveTypeLabel(value)
    }))
  )

  const timeframeToMs: Record<'24h' | '7d' | '30d' | 'all', number> = {
    '24h': 24 * 60 * 60 * 1000,
    '7d': 7 * 24 * 60 * 60 * 1000,
    '30d': 30 * 24 * 60 * 60 * 1000,
    all: Number.POSITIVE_INFINITY
  }

  const matchSearch = (row: TaskRow) => {
    const q = globalSearch.value.trim().toLowerCase()
    if (!q) return true
    return row.search_text.includes(q)
  }

  const matchCluster = (row: TaskRow) => {
    if (selectedCluster.value === 'all') return true
    return row.cluster_id === selectedCluster.value
  }

  const matchTimeframe = (row: TaskRow) => {
    if (selectedTimeframe.value === 'all') return true
    const cutoff = Date.now() - timeframeToMs[selectedTimeframe.value]
    const ts = row.last_update || row.start_time
    if (!ts) return false
    return new Date(ts).getTime() >= cutoff
  }

  const filteredAllTasks = computed(() =>
    baseRows.value
      .filter(row => {
        if (selectedTypes.value.size && !selectedTypes.value.has(row.type)) return false
        if (
          selectedArchiveSubtypes.value.size &&
          (row.type !== 'archive' || !row.subtype || !selectedArchiveSubtypes.value.has(row.subtype))
        ) {
          return false
        }
        if (selectedStatuses.value.size && !selectedStatuses.value.has(row.status)) return false
        if (!matchCluster(row)) return false
        if (!matchTimeframe(row)) return false
        if (!matchSearch(row)) return false
        return true
      })
      .sort(
        (a, b) =>
          new Date(b.last_update || b.start_time || 0).getTime() -
          new Date(a.last_update || a.start_time || 0).getTime()
      )
  )

  const activeSummary = computed(() => {
    const chips: string[] = []
    if (globalSearch.value.trim()) {
      chips.push(`关键词: ${globalSearch.value.trim()}`)
    }
    if (selectedCluster.value !== 'all') {
      const item = clusterOptions.value.find(opt => opt.value === selectedCluster.value)
      if (item) chips.push(`集群: ${item.label}`)
    }
    if (selectedStatuses.value.size) {
      const labels = statusOptions.value
        .filter(opt => selectedStatuses.value.has(opt.value))
        .map(opt => opt.label)
      if (labels.length) chips.push(`状态: ${labels.join(' / ')}`)
    }
    if (selectedTypes.value.size) {
      const labels = typeOptions.value
        .filter(opt => selectedTypes.value.has(opt.value))
        .map(opt => opt.label)
      if (labels.length) chips.push(`类型: ${labels.join(' / ')}`)
    }
    if (selectedArchiveSubtypes.value.size) {
      const labels = archiveSubtypeOptions.value
        .filter(opt => selectedArchiveSubtypes.value.has(opt.value))
        .map(opt => opt.label)
      if (labels.length) chips.push(`归档子类型: ${labels.join(' / ')}`)
    }
    if (selectedTimeframe.value !== 'all') {
      const item = timeframeOptions.find(opt => opt.value === selectedTimeframe.value)
      if (item) chips.push(item.label)
    }
    return chips
  })

  const resetFilters = () => {
    selectedStatuses.value.clear()
    selectedTypes.value.clear()
    selectedArchiveSubtypes.value.clear()
    selectedCluster.value = 'all'
    selectedTimeframe.value = 'all'
    globalSearch.value = ''
  }

  const toggleStatus = (status: string) => {
    const set = selectedStatuses.value
    set.has(status) ? set.delete(status) : set.add(status)
  }

  const toggleType = (type: string) => {
    const set = selectedTypes.value
    set.has(type) ? set.delete(type) : set.add(type)
  }

  const toggleArchiveSubtype = (subtype: string) => {
    const set = selectedArchiveSubtypes.value
    set.has(subtype) ? set.delete(subtype) : set.add(subtype)
  }

  return {
    globalSearch,
    selectedStatuses,
    selectedTypes,
    selectedArchiveSubtypes,
    selectedCluster,
    selectedTimeframe,
    statusOptions,
    typeOptions,
    archiveSubtypeOptions,
    clusterOptions,
    timeframeOptions,
    statusCounts,
    typeCounts,
    archiveSubtypeCounts,
    filteredAllTasks,
    activeSummary,
    toggleStatus,
    toggleType,
    toggleArchiveSubtype,
    resetFilters
  }
}
