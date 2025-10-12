import { ref } from 'vue'
import type { Ref } from 'vue'
import { tasksApi, type MergeTask } from '@/api/tasks'
import { clustersApi, type Cluster } from '@/api/clusters'
import { scanTasksApi, type ScanTask } from '@/api/scanTasks'
import { tablesApi } from '@/api/tables'
import { useMonitoringStore } from '@/stores/monitoring'

/**
 * 任务数据获取和管理
 */
export function useTasksData() {
  const monitoringStore = useMonitoringStore()

  // 数据状态
  const tasks = ref<MergeTask[]>([])
  const testTableTasks = ref<any[]>([])
  const scanTasks = ref<ScanTask[]>([])
  const archiveTasks = ref<any[]>([])
  const clusters = ref<Cluster[]>([])

  // 加载状态
  const loading = ref(false)
  const loadingScan = ref(false)

  /**
   * 加载合并任务
   */
  const loadTasks = async (clusterId?: number | null) => {
    loading.value = true
    try {
      if (!clusterId) {
        tasks.value = []
        testTableTasks.value = []
        return
      }

      const allTasks = await tasksApi.list({ cluster_id: clusterId })
      tasks.value = allTasks.filter((item: any) => !item.type || item.type === 'merge')
      testTableTasks.value = allTasks.filter((item: any) => item.type === 'test-table-generation')
    } catch (error) {
      console.error('Failed to load tasks:', error)
    } finally {
      loading.value = false
    }
  }

  /**
   * 加载扫描任务
   */
  const loadScanTasks = async (clusterFilter?: number | null, statusFilter?: string) => {
    loadingScan.value = true
    try {
      const cid = clusterFilter || undefined
      if (!cid) {
        scanTasks.value = []
        return
      }
      const status = statusFilter || undefined
      scanTasks.value = await scanTasksApi.list(cid as any, status)
    } catch (error) {
      console.error('Failed to load scan tasks:', error)
    } finally {
      loadingScan.value = false
    }
  }

  /**
   * 加载归档任务
   */
  const loadArchiveTasks = async () => {
    try {
      archiveTasks.value = []
      const cid = monitoringStore.settings.selectedCluster
      if (!cid) return
      const res: any = await tablesApi.getArchivedTables(cid, 200)
      const list = res?.archived_tables || res?.items || []
      archiveTasks.value = list.map((t: any) => ({
        cluster_id: cid,
        database_name: t.database_name,
        table_name: t.table_name,
        archived_at: t.archived_at,
        archive_location: t.archive_location,
        task_name: `归档 ${t.database_name}.${t.table_name}`
      }))
    } catch (e) {
      console.error('Failed to load archive tasks:', e)
    }
  }

  /**
   * 加载集群列表
   */
  const loadClusters = async () => {
    try {
      clusters.value = await clustersApi.list()
    } catch (error) {
      console.error('Failed to load clusters:', error)
    }
  }

  /**
   * 刷新归档摘要信息
   */
  const archiveSummaries = ref<Record<string, any>>({})

  const refreshArchiveSummaries = async () => {
    const candidates = (scanTasks.value || []).filter((t: any) =>
      ['archive-table', 'restore-table', 'archive-table-policy', 'restore-table-policy'].includes(String(t.task_type))
    )

    for (const t of candidates) {
      const tid = t.task_id
      if (!tid) continue
      if (archiveSummaries.value[tid] && (t.status === 'completed' || t.status === 'failed')) continue

      try {
        const logs = await scanTasksApi.getLogs(tid)
        const acc: any = {}

        for (const l of logs || []) {
          const msg = String(l.message || '')
          const m = msg.match(/\]\s*(\w+)\s+/)
          const code = m ? m[1] : undefined
          const ctx: Record<string, string> = {}
          const kvRe = /(\w+)=([^\s]+)/g
          let mm
          while ((mm = kvRe.exec(msg)) !== null) {
            ctx[mm[1]] = mm[2]
          }

          if (!code || !ctx) continue

          if (code === 'A150') {
            if (ctx.files_moved) acc.files_moved = Number(ctx.files_moved)
            if (ctx.archive_location) acc.archive_location = ctx.archive_location
          }
          if (code === 'PL120') {
            if (ctx.paths_success) acc.paths_success = Number(ctx.paths_success)
            if (ctx.paths_failed) acc.paths_failed = Number(ctx.paths_failed)
            if (ctx.effective) acc.effective = ctx.effective
          }
          if (code === 'AR190') {
            if (ctx.files_restored) acc.files_restored = Number(ctx.files_restored)
            if (ctx.restored_location) acc.restored_location = ctx.restored_location
          }
        }

        if (Object.keys(acc).length) {
          archiveSummaries.value[tid] = { ...(archiveSummaries.value[tid] || {}), ...acc }
        }
      } catch (e) {
        // 忽略日志加载失败
      }
    }
  }

  return {
    // 数据
    tasks,
    testTableTasks,
    scanTasks,
    archiveTasks,
    clusters,
    archiveSummaries,

    // 状态
    loading,
    loadingScan,

    // 方法
    loadTasks,
    loadScanTasks,
    loadArchiveTasks,
    loadClusters,
    refreshArchiveSummaries
  }
}
