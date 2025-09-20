<template>
  <div class="tables">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="header-actions">
            <span v-if="currentClusterName" class="current-cluster">当前集群：{{ currentClusterName }}</span>
            <el-select
              v-model="selectedDatabase"
              placeholder="选择数据库"
              style="width: 220px; margin-right: 8px"
              :disabled="!databases.length"
            >
              <el-option v-for="db in databases" :key="db" :label="db" :value="db" />
            </el-select>
            <el-input v-model="searchText" placeholder="搜索表名..." clearable style="width: 260px">
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-dropdown split-button type="primary" @click="onScanDefault" @command="handleScanCommand" style="margin-left: 8px">
              扫描
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :disabled="!selectedDatabase" command="db-strict">扫描当前库（严格）</el-dropdown-item>
                  <el-dropdown-item :disabled="!selectedDatabase" command="db-fallback">扫描当前库（允许降级）</el-dropdown-item>
                  <el-dropdown-item divided command="cluster-strict">全集群扫描（严格）</el-dropdown-item>
                  <el-dropdown-item command="cluster-fallback">全集群扫描（允许降级）</el-dropdown-item>
                  <el-dropdown-item divided command="settings">高级设置…</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-dropdown :disabled="!selectedRows.length" style="margin-left: 8px" @command="cmd => cmd==='bulk-merge' && bulkCreateMergeTasks()">
              <span class="el-dropdown-link">
                批量操作<el-icon class="el-icon--right"><Operation /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-if="activeTab==='merge'" command="bulk-merge" :disabled="!selectedRows.length">批量创建合并任务</el-dropdown-item>
                  <el-dropdown-item v-else disabled>批量归档（稍后提供）</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-popover placement="bottom-end" trigger="click">
              <template #reference>
                <el-button plain style="margin-left:8px">筛选器</el-button>
              </template>
              <div class="filter-pop">
                <el-checkbox v-model="filterPartitioned">仅分区表</el-checkbox>
                <el-checkbox v-model="filterSmall">仅有小文件</el-checkbox>
                <el-checkbox v-model="filterArchivedOnly">仅已归档</el-checkbox>
                <el-checkbox v-model="filterColdOnly">仅冷数据</el-checkbox>
                <div style="margin-top:8px;color:#606266">小文件占比 ≥ {{ smallRatioMin }}%</div>
                <el-slider v-model="smallRatioMin" :min="0" :max="100" :step="5" style="width:220px" />
              </div>
            </el-popover>
            <el-popover placement="bottom-end" trigger="click">
              <template #reference>
                <el-button plain style="margin-left:8px">列</el-button>
              </template>
              <div v-if="activeTab==='merge'" class="cols-pop">
                <el-checkbox v-model="columnsMerge.small">小文件数</el-checkbox>
                <el-checkbox v-model="columnsMerge.ratio">小文件占比</el-checkbox>
                <el-checkbox v-model="columnsMerge.total_files">总文件数</el-checkbox>
                <el-checkbox v-model="columnsMerge.total_size">总大小</el-checkbox>
                <el-checkbox v-model="columnsMerge.partitioned">分区表</el-checkbox>
                <el-checkbox v-model="columnsMerge.partition_count">分区数</el-checkbox>
                <el-checkbox v-model="columnsMerge.scan_time">扫描时间</el-checkbox>
                <el-checkbox v-model="columnsMerge.actions">操作列</el-checkbox>
              </div>
              <div v-else class="cols-pop">
                <el-checkbox v-model="columnsArchive.cold">冷数据</el-checkbox>
                <el-checkbox v-model="columnsArchive.cold_days">未访问天数</el-checkbox>
                <el-checkbox v-model="columnsArchive.archived">归档状态</el-checkbox>
                <el-checkbox v-model="columnsArchive.archive_location">归档位置</el-checkbox>
                <el-checkbox v-model="columnsArchive.archived_at">归档时间</el-checkbox>
                <el-checkbox v-model="columnsArchive.actions">操作列</el-checkbox>
              </div>
            </el-popover>
            <span class="last-updated">更新于 {{ lastUpdated || '-' }}</span>
            <el-button v-if="currentTaskId" type="info" plain @click="showProgress = true" style="margin-left: 8px">查看进度</el-button>
            <el-button class="cloudera-btn secondary" @click="loadTableMetrics" style="margin-left: 8px">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 主体内容：页签 + 表格 + 分页（保留原有） -->
      <div class="main-content">
          <el-tabs v-model="activeTab">
            <el-tab-pane label="小文件/合并" name="merge">
              <el-table :data="displayRowsMerge" stripe v-loading="loading" @selection-change="onSelectionChange">
                <el-table-column type="selection" width="44" />
                <el-table-column prop="database_name" label="数据库" width="120" v-if="columnsMerge.db" />
                <el-table-column prop="table_name" label="表名" width="200" v-if="columnsMerge.table">
                  <template #default="{ row }">
                    <router-link :to="`/tables/${clusterId}/${row.database_name}/${row.table_name}`" class="table-name-link">
                      {{ row.table_name }}
                    </router-link>
                  </template>
                </el-table-column>
                <el-table-column prop="small_files" label="小文件数" width="100" v-if="columnsMerge.small">
                  <template #default="{ row }">
                    <span :class="{ 'text-danger': row.small_files > 0 }">{{ row.small_files }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="small_file_ratio" label="小文件占比" width="120" v-if="columnsMerge.ratio">
                  <template #default="{ row }">
                    <el-progress :percentage="calcSmallFilePercent(row)" :color="getProgressColor(calcSmallFilePercent(row))" :show-text="true" style="width: 80px" />
                  </template>
                </el-table-column>
                <el-table-column prop="total_files" label="总文件数" width="100" v-if="columnsMerge.total_files" />
                <el-table-column prop="total_size" label="总大小" width="110" v-if="columnsMerge.total_size">
                  <template #default="{ row }">{{ formatSize(row.total_size) }}</template>
                </el-table-column>
                <el-table-column prop="is_partitioned" label="分区表" width="80" v-if="columnsMerge.partitioned">
                  <template #default="{ row }">
                    <el-tag :type="row.is_partitioned ? 'success' : 'info'" size="small">{{ row.is_partitioned ? '是' : '否' }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="分区数" width="90" sortable :sort-by="partitionCountSortKey" v-if="columnsMerge.partition_count">
                  <template #default="{ row }">{{ row.is_partitioned ? (row.partition_count ?? 0) : -1 }}</template>
                </el-table-column>
                <el-table-column prop="scan_time" label="扫描时间" width="160" v-if="columnsMerge.scan_time">
                  <template #default="{ row }">{{ formatTime(row.scan_time) }}</template>
                </el-table-column>
                <el-table-column label="操作" width="160" v-if="columnsMerge.actions">
                  <template #default="{ row }">
                    <el-button type="primary" size="small" @click="createMergeTask(row)">创建合并任务</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="归档" name="archive">
              <el-table :data="displayRowsArchive" stripe v-loading="loading" @selection-change="onSelectionChange">
                <el-table-column type="selection" width="44" />
                <el-table-column prop="database_name" label="数据库" width="120" v-if="columnsArchive.db" />
                <el-table-column prop="table_name" label="表名" width="200" v-if="columnsArchive.table" />
                <el-table-column label="冷数据" width="120" v-if="columnsArchive.cold">
                  <template #default="{ row }">
                    <el-tag v-if="row.is_cold_data" type="warning" size="small">冷数据</el-tag>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column label="未访问天数" width="120" v-if="columnsArchive.cold_days">
                  <template #default="{ row }">{{ row.days_since_last_access ?? '-' }}</template>
                </el-table-column>
                <el-table-column label="归档状态" width="100" v-if="columnsArchive.archived">
                  <template #default="{ row }">
                    <el-tag v-if="row.archive_status === 'archived'" type="danger" size="small">已归档</el-tag>
                    <el-tag v-else type="primary" size="small">活跃中</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="archive_location" label="归档位置" min-width="240" show-overflow-tooltip v-if="columnsArchive.archive_location" />
                <el-table-column label="归档时间" width="160" v-if="columnsArchive.archived_at">
                  <template #default="{ row }">{{ formatTime(row.archived_at) }}</template>
                </el-table-column>
                <el-table-column label="操作" width="200" v-if="columnsArchive.actions">
                  <template #default="{ row }">
                    <el-button v-if="row.archive_status !== 'archived'" type="warning" size="small" @click="archiveTable(row)" :loading="row.archiving">归档</el-button>
                    <el-button v-else type="success" size="small" @click="restoreTable(row)" :loading="row.restoring">恢复</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
          </el-tabs>
          <!-- 分页（两个页签共用，同步 URL） -->
          <div class="pagination-wrapper" v-if="total > 0">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[20, 50, 100, 200]"
              :total="total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="reloadPage"
              @current-change="reloadPage"
            />
          </div>
        </div>

      <!-- 扫描高级设置弹窗（仅设置每库最大表数） -->
      <el-dialog v-model="showScanSettings" title="扫描设置" width="420px">
        <div class="wizard-row">
          <div class="label">每库最大表数</div>
          <el-input-number v-model="maxPerDb" :min="0" :step="10" />
          <span style="margin-left:8px;color:#909399">0 表示不限</span>
        </div>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showScanSettings = false">关闭</el-button>
          </span>
        </template>
      </el-dialog>
      
    </el-card>
  </div>
  <TaskRunDialog
    v-model="showProgress"
    :type="runDialogType"
    :scan-task-id="currentTaskId || undefined"
  />
</template>

<script setup lang="ts">
  import { ref, onMounted, watch, computed } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { tablesApi, type TableMetric } from '@/api/tables'
  import { clustersApi } from '@/api/clusters'
  import { tasksApi } from '@/api/tasks'
  import dayjs from 'dayjs'
  import TaskRunDialog from '@/components/TaskRunDialog.vue'
  import { useMonitoringStore } from '@/stores/monitoring'
  import { Search, Filter, Operation } from '@element-plus/icons-vue'

  // 数据
  const route = useRoute()
  const router = useRouter()
  const monitoringStore = useMonitoringStore()
  const clusterId = computed(() => monitoringStore.settings.selectedCluster)

  const tableItems = ref<TableMetric[]>([])
  const total = ref(0)
  const archiveItems = ref<TableMetric[]>([])
  const archiveTotal = ref(0)
  const searchText = ref('')
  const dbSearch = ref('')
  const filterPartitioned = ref(false)
  const filterSmall = ref(false)
  const filterArchivedOnly = ref(false)
  const filterColdOnly = ref(false)
  const activeTab = ref<'merge' | 'archive'>('merge')
  const databases = ref<string[]>([])
  const selectedDatabase = ref<string | ''>('')
  const loading = ref(false)
  const scanMode = ref<'strict' | 'fallback'>('strict')
  const scanScope = ref<'db' | 'cluster'>('db')
  const scanning = ref(false)
  const strictRealFlag = computed(() => scanMode.value === 'strict')
  const showScanSettings = ref(false)
  const showProgress = ref(false)
  const currentTaskId = ref<string | null>(null)
  const runDialogType = ref<'scan'|'archive'>('scan')
  const maxPerDb = ref<number>(20)
  const currentPage = ref(1)
  const pageSize = ref(50)
  const lastUpdated = ref('')
  const currentClusterName = ref('')

  // 选择与批量
  const selectedRows = ref<TableMetric[]>([])
  const onSelectionChange = (rows: TableMetric[]) => {
    selectedRows.value = rows
  }

  // 筛选器与占比阈值
  const smallRatioMin = ref(0)

  // 列可见性（持久化）
  const columnKeyMerge = 'tables-columns-merge'
  const columnKeyArchive = 'tables-columns-archive'
  const columnsMerge = ref<Record<string, boolean>>({
    db: true,
    table: true,
    small: true,
    ratio: true,
    total_files: true,
    total_size: true,
    partitioned: true,
    partition_count: true,
    scan_time: true,
    actions: true,
  })
  const columnsArchive = ref<Record<string, boolean>>({
    db: true,
    table: true,
    cold: true,
    cold_days: true,
    archived: true,
    archive_location: false,
    archived_at: true,
    actions: true,
  })
  const loadColumnPrefs = () => {
    try {
      const m = localStorage.getItem(columnKeyMerge)
      if (m) Object.assign(columnsMerge.value, JSON.parse(m))
      const a = localStorage.getItem(columnKeyArchive)
      if (a) Object.assign(columnsArchive.value, JSON.parse(a))
    } catch {}
  }
  const saveColumnPrefs = () => {
    try {
      localStorage.setItem(columnKeyMerge, JSON.stringify(columnsMerge.value))
      localStorage.setItem(columnKeyArchive, JSON.stringify(columnsArchive.value))
    } catch {}
  }

  const filteredDatabases = computed(() => {
    const kw = (dbSearch.value || '').toLowerCase()
    return databases.value.filter(db => !kw || db.toLowerCase().includes(kw))
  })

  const selectDb = (db: string) => {
    selectedDatabase.value = db
  }

  const displayRowsMerge = computed(() => {
    return tableItems.value.filter((row) => {
      if (filterArchivedOnly.value || filterColdOnly.value) return false
      const okPartitioned = !filterPartitioned.value || !!row.is_partitioned
      const okSmall = !filterSmall.value || (Number(row.small_files || 0) > 0)
      const okSearch = !searchText.value || `${row.database_name}.${row.table_name}`.toLowerCase().includes(searchText.value.toLowerCase())
      const ratio = calcSmallFilePercent(row)
      const okRatio = ratio >= smallRatioMin.value
      return okPartitioned && okSmall && okSearch && okRatio
    })
  })

  const displayRowsArchive = computed(() => {
    return archiveItems.value.filter((row) => {
      const okSearch = !searchText.value || `${row.database_name}.${row.table_name}`
        .toLowerCase()
        .includes(searchText.value.toLowerCase())
      // 冷/归档页签不对分区/小文件做硬过滤，仅保留搜索
      return okSearch
    })
  })

  // 方法
  const loadTableMetrics = async () => {
    if (!clusterId.value) return

    loading.value = true
    try {
      const res = await tablesApi.getTableMetrics({
        cluster_id: clusterId.value as number,
        database_name: selectedDatabase.value || undefined,
        page: currentPage.value,
        page_size: pageSize.value,
      })
      tableItems.value = res.items || []
      total.value = res.total || 0
      lastUpdated.value = dayjs().format('YYYY-MM-DD HH:mm:ss')
    } catch (error) {
      console.error('Failed to load table metrics:', error)
    } finally {
      loading.value = false
    }
  }

  // 加载归档/冷数据列表
  const loadArchiveData = async () => {
    if (!clusterId.value) return
    loading.value = true
    try {
      // 优先显示：仅已归档 -> 走已归档列表；否则默认展示冷数据列表
      if (filterArchivedOnly.value) {
        const lim = pageSize.value * currentPage.value
        const res: any = await tablesApi.getArchivedTables(clusterId.value as number, lim)
        const list = (res && (res.archived_tables || res.items)) || []
        const totalCount = Number(res?.total_archived_tables || list.length)
        const start = (currentPage.value - 1) * pageSize.value
        const end = start + pageSize.value
        const pageSlice = list.slice(start, end)
        archiveItems.value = pageSlice.map((t: any) => ({
          id: 0,
          cluster_id: clusterId.value as number,
          database_name: t.database_name,
          table_name: t.table_name,
          table_path: '',
          total_files: Number(t.total_files || 0),
          small_files: Number(t.small_files || 0),
          total_size: Number(t.total_size || 0),
          avg_file_size: 0,
          is_partitioned: false,
          partition_count: 0,
          scan_time: '',
          scan_duration: 0,
          is_cold_data: false,
          days_since_last_access: t.days_since_last_access ?? t.days_since_access,
          last_access_time: t.last_access_time,
          archive_status: 'archived',
          archive_location: t.archive_location,
          archived_at: t.archived_at,
        }))
        archiveTotal.value = totalCount
        total.value = archiveTotal.value
      } else {
        const res: any = await tablesApi.getColdDataList(
          clusterId.value as number,
          currentPage.value,
          pageSize.value
        )
        const list = (res && (res.cold_tables || res.items)) || []
        archiveItems.value = list.map((t: any) => ({
          id: t.id || 0,
          cluster_id: clusterId.value as number,
          database_name: t.database_name,
          table_name: t.table_name,
          table_path: t.table_path || '',
          total_files: Number(t.total_files || 0),
          small_files: Number(t.small_files || 0),
          total_size: Number(t.total_size || 0),
          avg_file_size: 0,
          is_partitioned: false,
          partition_count: 0,
          scan_time: t.scan_time || '',
          scan_duration: 0,
          is_cold_data: true,
          days_since_last_access: t.days_since_last_access ?? t.days_since_access,
          last_access_time: t.last_access_time,
          archive_status: t.archive_status || 'active',
          archive_location: t.archive_location,
          archived_at: t.archived_at,
        }))
        archiveTotal.value = Number(res?.total || archiveItems.value.length)
        total.value = archiveTotal.value
      }
      lastUpdated.value = dayjs().format('YYYY-MM-DD HH:mm:ss')
    } catch (e) {
      console.error('Failed to load archive data:', e)
    } finally {
      loading.value = false
    }
  }

  const loadCurrentClusterName = async () => {
    try {
      if (!clusterId.value) {
        currentClusterName.value = ''
        return
      }
      const cluster = await clustersApi.get(clusterId.value as number)
      currentClusterName.value = cluster?.name || ''
    } catch {
      currentClusterName.value = ''
    }
  }

  const loadDatabases = async () => {
    if (!clusterId.value) return
    try {
      const list = await tablesApi.getDatabases(clusterId.value as number)
      // API 返回 { databases: string[] }
      databases.value = Array.isArray((list as any).databases)
        ? (list as any).databases
        : (list as any)
      if (databases.value.length && !selectedDatabase.value) {
        selectedDatabase.value = databases.value[0]
      }
    } catch (error) {
      console.error('Failed to load databases:', error)
    }
  }

  const reloadPage = () => {
    if (activeTab.value === 'archive') {
      loadArchiveData()
    } else {
      loadTableMetrics()
    }
    // 更新路由状态
    const flags: string[] = []
    if (filterPartitioned.value) flags.push('partitioned')
    if (filterSmall.value) flags.push('small')
    if (filterArchivedOnly.value) flags.push('archived')
    if (filterColdOnly.value) flags.push('cold')
    router.replace({
      query: {
        ...route.query,
        db: selectedDatabase.value || '',
        q: searchText.value || '',
        tab: activeTab.value,
        page: String(currentPage.value),
        page_size: String(pageSize.value),
        mode: scanMode.value,
        scope: scanScope.value,
        max: String(maxPerDb.value || 0),
        flags: flags.join(','),
      },
    })
  }

  const triggerScan = async () => {
    if (!clusterId.value) {
      ElMessage.warning('请先选择集群')
      return
    }
    if (!selectedDatabase.value) {
      ElMessage.warning('请先选择数据库')
      return
    }

    try {
      await tablesApi.triggerScan(
        clusterId.value as number,
        selectedDatabase.value,
        undefined,
        strictRealFlag.value
      )
      ElMessage.success(`已启动扫描：${selectedDatabase.value}`)
      // 延迟刷新数据
      setTimeout(() => {
        loadTableMetrics()
      }, 2000)
    } catch (error) {
      console.error('Failed to trigger scan:', error)
    }
  }

  // 触发全库扫描（带进度）
  const triggerClusterScan = async () => {
    if (!clusterId.value) {
      ElMessage.warning('请先选择集群')
      return
    }
    try {
      const res = await tablesApi.scanAllDatabases(
        clusterId.value as number,
        strictRealFlag.value,
        maxPerDb.value
      )
      if (res && res.task_id) {
        currentTaskId.value = res.task_id
        showProgress.value = true
      } else {
        ElMessage.error('未获取到任务ID，无法追踪进度')
      }
    } catch (e) {
      console.error('Failed to start cluster scan:', e)
      ElMessage.error('启动全库扫描失败')
    }
  }

  const onClusterScanCompleted = () => {
    // 任务完成后刷新表格
    loadTableMetrics()
  }

  // 统一开始扫描入口
  const startScan = async () => {
    if (!clusterId.value) {
      ElMessage.warning('请先选择集群')
      return
    }
    if (scanScope.value === 'db' && !selectedDatabase.value) {
      ElMessage.warning('请选择数据库')
      return
    }
    scanning.value = true
    try {
      if (scanScope.value === 'db') {
        await tablesApi.triggerScan(
          clusterId.value as number,
          selectedDatabase.value,
          undefined,
          strictRealFlag.value
        )
        ElMessage.success(`已启动扫描：${selectedDatabase.value}`)
        setTimeout(() => loadTableMetrics(), 1500)
      } else {
        const res = await tablesApi.scanAllDatabases(
          clusterId.value as number,
          strictRealFlag.value,
          maxPerDb.value
        )
        if (res && res.task_id) {
          currentTaskId.value = res.task_id
          showProgress.value = true
          ElMessage.success('已启动全集群扫描')
        } else {
          ElMessage.error('未获取到任务ID，无法追踪进度')
        }
      }
    } catch (e) {
      console.error('Start scan failed:', e)
      ElMessage.error('启动扫描失败')
    } finally {
      scanning.value = false
    }
  }

  // 分裂按钮：主键行为（扫描当前库-严格）
  const onScanDefault = () => {
    scanScope.value = 'db'
    scanMode.value = 'strict'
    startScan()
  }

  // 分裂按钮：菜单项
  const handleScanCommand = (cmd: string) => {
    if (cmd === 'settings') {
      showScanSettings.value = true
      return
    }
    const map: Record<string, { scope: 'db' | 'cluster'; mode: 'strict' | 'fallback' }> = {
      'db-strict': { scope: 'db', mode: 'strict' },
      'db-fallback': { scope: 'db', mode: 'fallback' },
      'cluster-strict': { scope: 'cluster', mode: 'strict' },
      'cluster-fallback': { scope: 'cluster', mode: 'fallback' },
    }
    const opt = map[cmd]
    if (!opt) return
    scanScope.value = opt.scope
    scanMode.value = opt.mode
    startScan()
  }

  const createMergeTask = (table: TableMetric) => {
    // TODO: 实现创建合并任务的逻辑
    ElMessage.info(`准备为表 ${table.database_name}.${table.table_name} 创建合并任务`)
  }

  // 归档表
  const archiveTable = async (table: TableMetric) => {
    try {
      await ElMessageBox.confirm(
        `确定要归档表 ${table.database_name}.${table.table_name} 吗？这将把表数据移动到归档存储区。`,
        '归档确认',
        {
          confirmButtonText: '确定归档',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )

      table.archiving = true
      const response = await tablesApi.archiveTableWithProgress(
        clusterId.value as number,
        table.database_name,
        table.table_name,
        true
      )

      if (response && response.task_id) {
        currentTaskId.value = response.task_id
        runDialogType.value = 'archive'
        showProgress.value = true
        ElMessage.success('已启动表归档任务')
      } else {
        ElMessage.error('未获取到任务ID，无法追踪进度')
      }
    } catch (error) {
      if (error !== 'cancel') {
        console.error('归档表失败:', error)
        ElMessage.error('归档表失败: ' + ((error as any)?.message || error))
      }
    } finally {
      table.archiving = false
    }
  }

  // 恢复表
  const restoreTable = async (table: TableMetric) => {
    try {
      await ElMessageBox.confirm(
        `确定要恢复表 ${table.database_name}.${table.table_name} 吗？这将把归档的数据移回原始存储位置。`,
        '恢复确认',
        {
          confirmButtonText: '确定恢复',
          cancelButtonText: '取消',
          type: 'info'
        }
      )

      table.restoring = true
      await tablesApi.restoreTable(
        clusterId.value as number,
        table.database_name,
        table.table_name
      )

      ElMessage.success(`表 ${table.database_name}.${table.table_name} 恢复成功`)

      // 更新表状态
      table.archive_status = 'active'
      table.archive_location = null as any
      table.archived_at = null as any
    } catch (error) {
      if (error !== 'cancel') {
        console.error('恢复表失败:', error)
        ElMessage.error('恢复表失败: ' + (error as any)?.message || error)
      }
    } finally {
      table.restoring = false
    }
  }

  const formatSize = (bytes: number): string => {
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    let size = bytes
    let unitIndex = 0

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }

    return `${size.toFixed(1)} ${units[unitIndex]}`
  }

  const formatTime = (time: string): string => {
    return dayjs(time).format('MM-DD HH:mm')
  }

  // 排序：分区数（非分区为 -1）
  const partitionCountSortKey = (row: TableMetric): number => {
    return row.is_partitioned ? (row.partition_count ?? 0) : -1
  }

  const getProgressColor = (percentage: number): string => {
    if (percentage > 80) return '#f56c6c'
    if (percentage > 50) return '#e6a23c'
    if (percentage > 20) return '#1989fa'
    return '#67c23a'
  }

  // 计算小文件比例（避免除以 0/NaN）
  const calcSmallFilePercent = (row: TableMetric): number => {
    const total = Number(row.total_files || 0)
    const small = Number(row.small_files || 0)
    if (!total || total <= 0) return 0
    const pct = (small / total) * 100
    if (!isFinite(pct) || isNaN(pct)) return 0
    return Math.max(0, Math.min(100, Math.round(pct)))
  }

  // 监听集群变化
  // 初始化：从路由恢复状态
  onMounted(async () => {
    loadColumnPrefs()
    // 初始tab/db/q/page
    const q = route.query
    if (typeof q.tab === 'string' && (q.tab === 'merge' || q.tab === 'archive')) activeTab.value = q.tab
    if (typeof q.db === 'string') selectedDatabase.value = q.db
    if (typeof q.q === 'string') searchText.value = q.q
    if (typeof q.page === 'string') currentPage.value = parseInt(q.page) || 1
    if (typeof q.page_size === 'string') pageSize.value = parseInt(q.page_size) || 50
    if (typeof q.mode === 'string' && (q.mode === 'strict' || q.mode === 'fallback')) scanMode.value = q.mode
    if (typeof q.scope === 'string' && (q.scope === 'db' || q.scope === 'cluster')) scanScope.value = q.scope
    if (typeof q.max === 'string') maxPerDb.value = parseInt(q.max) || 0
    if (typeof q.flags === 'string') {
      const set = new Set(q.flags.split(',').filter(Boolean))
      filterPartitioned.value = set.has('partitioned')
      filterSmall.value = set.has('small')
      filterArchivedOnly.value = set.has('archived')
      filterColdOnly.value = set.has('cold')
    }

    await loadCurrentClusterName()
    await loadDatabases()
    await loadTableMetrics()
    await loadArchiveData()
  })

  // 响应数据库变更
  watch(selectedDatabase, () => {
    currentPage.value = 1
    loadTableMetrics()
    reloadPage()
  })

  // 集群变化时刷新只读集群名称
  watch(clusterId, () => {
    loadCurrentClusterName()
    if (activeTab.value === 'archive') {
      loadArchiveData()
    } else {
      loadTableMetrics()
    }
  })

  // 其他筛选/搜索/标签切换变更后同步路由
  watch([searchText, filterPartitioned, filterSmall, filterArchivedOnly, filterColdOnly, activeTab], () => {
    currentPage.value = 1
    reloadPage()
  })
  watch([columnsMerge, columnsArchive], saveColumnPrefs, { deep: true })

  // 分页变化时，按当前页签加载数据
  watch([currentPage, pageSize], () => {
    if (activeTab.value === 'archive') {
      loadArchiveData()
    } else {
      loadTableMetrics()
    }
  })

  const bulkWorking = ref(false)
  const bulkCreateMergeTasks = async () => {
    if (!clusterId.value || !selectedRows.value.length) return
    bulkWorking.value = true
    try {
      for (const row of selectedRows.value) {
        await tasksApi.create({
          cluster_id: clusterId.value as number,
          task_name: `merge_${row.database_name}.${row.table_name}`,
          database_name: row.database_name,
          table_name: row.table_name,
          merge_strategy: 'safe_merge',
        })
      }
      ElMessage.success(`已创建 ${selectedRows.value.length} 个合并任务`)
    } catch (e) {
      console.error(e)
      ElMessage.error('批量创建任务失败')
    } finally {
      bulkWorking.value = false
    }
  }

  
</script>

<style scoped>
  .card-header {
    display: flex;
    justify-content: flex-start;
    align-items: center;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .text-danger {
    color: #f56c6c;
    font-weight: 600;
  }

  .table-name-link {
    color: #409eff;
    text-decoration: none;
    font-weight: 500;
    transition: all 0.2s ease;
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
  }

  .table-name-link:hover {
    color: #66b1ff;
    background-color: #f0f9ff;
    transform: translateX(2px);
    text-decoration: underline;
  }

  .filters-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 12px 0;
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }

  .scan-controls {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    margin: 8px 0 16px;
  }
  .control-group {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .control-group .label {
    color: #606266;
    font-size: 13px;
  }
  .control-actions {
    margin-left: auto;
    display: inline-flex;
    gap: 8px;
  }

  /* 新布局样式 */
  /* 布局容器（单列主区） */
  .main-content {
    flex: 1;
    min-width: 0;
  }
  .last-updated { color: #909399; margin-left: 12px; font-size: 12px; }
  .current-cluster { color: #606266; margin-right: 8px; font-size: 13px; }
  .cols-pop, .filter-pop { display: flex; flex-direction: column; gap: 6px; }
  .empty-hint { color: #909399; font-size: 12px; padding: 8px; }
  .wizard-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
  .wizard-row .label { width: 88px; color: #606266; text-align: right; }
</style>
