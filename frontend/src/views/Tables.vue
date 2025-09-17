<template>
  <div class="tables">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>表管理</span>
          <div class="header-actions">
            <el-select v-model="selectedCluster" placeholder="选择集群" style="width: 200px; margin-right: 10px;">
              <el-option
                v-for="cluster in clusters"
                :key="cluster.id"
                :label="cluster.name"
                :value="cluster.id"
              />
            </el-select>
            <el-select v-model="selectedDatabase" placeholder="选择数据库" style="width: 220px; margin-right: 10px;" :disabled="!databases.length">
              <el-option
                v-for="db in databases"
                :key="db"
                :label="db"
                :value="db"
              />
            </el-select>
            <el-switch
              v-model="strictReal"
              active-text="严格实连"
              inactive-text="允许Mock"
              style="margin-right: 12px;"
            />
            <el-button type="primary" @click="triggerScan">
              <el-icon><Refresh /></el-icon>
              扫描
            </el-button>
            <el-select v-model="maxPerDb" placeholder="每库表数" style="width: 120px; margin-left: 8px;">
              <el-option :value="0" label="不限制" />
              <el-option :value="10" label="10/库" />
              <el-option :value="20" label="20/库" />
              <el-option :value="50" label="50/库" />
              <el-option :value="100" label="100/库" />
            </el-select>
            <el-button type="success" @click="triggerClusterScan" style="margin-left: 8px;">
              <el-icon><Refresh /></el-icon>
              全库扫描(进度)
            </el-button>
            <el-button type="warning" @click="triggerColdDataScan" style="margin-left: 8px;">
              <el-icon><Snowflake /></el-icon>
              冷数据扫描
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="tableMetrics" stripe v-loading="loading">
        <el-table-column prop="database_name" label="数据库" width="120" />
        <el-table-column prop="table_name" label="表名" width="200">
          <template #default="{ row }">
            <router-link 
              :to="`/tables/${selectedCluster}/${row.database_name}/${row.table_name}`"
              class="table-name-link"
            >
              {{ row.table_name }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column prop="total_files" label="总文件数" width="100" />
        <el-table-column prop="small_files" label="小文件数" width="100">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.small_files > 0 }">
              {{ row.small_files }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="small_file_ratio" label="小文件占比" width="120">
          <template #default="{ row }">
            <el-progress
              :percentage="calcSmallFilePercent(row)"
              :color="getProgressColor(calcSmallFilePercent(row))"
              :show-text="true"
              style="width: 80px;"
            />
          </template>
        </el-table-column>
        <el-table-column prop="total_size" label="总大小" width="100">
          <template #default="{ row }">
            {{ formatSize(row.total_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="is_partitioned" label="分区表" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_partitioned ? 'success' : 'info'" size="small">
              {{ row.is_partitioned ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分区数" width="90" sortable :sort-by="partitionCountSortKey">
          <template #default="{ row }">
            {{ row.is_partitioned ? (row.partition_count ?? 0) : -1 }}
          </template>
        </el-table-column>
        <el-table-column prop="scan_time" label="扫描时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.scan_time) }}
          </template>
        </el-table-column>
        <el-table-column label="冷数据状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.is_cold_data" type="warning" size="small" effect="dark">
              <el-icon><Snowflake /></el-icon>
              冷数据
            </el-tag>
            <el-tag v-else-if="row.days_since_last_access > 0" type="success" size="small">
              {{ row.days_since_last_access }}天前
            </el-tag>
            <el-tag v-else type="info" size="small">活跃</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="归档状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.archive_status === 'archived'" type="danger" size="small">
              <el-icon><FolderRemove /></el-icon>
              已归档
            </el-tag>
            <el-tag v-else type="primary" size="small">活跃中</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="createMergeTask(row)">
              创建合并任务
            </el-button>
            <el-button
              v-if="row.is_cold_data && row.archive_status !== 'archived'"
              type="warning"
              size="small"
              @click="archiveTable(row)"
              :loading="row.archiving"
            >
              <el-icon><FolderAdd /></el-icon>
              归档
            </el-button>
            <el-button
              v-if="row.archive_status === 'archived'"
              type="success"
              size="small"
              @click="restoreTable(row)"
              :loading="row.restoring"
            >
              <el-icon><FolderOpened /></el-icon>
              恢复
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
  <ScanProgressDialog
    v-model="showProgress"
    :task-id="currentTaskId || undefined"
    @completed="onClusterScanCompleted"
  />
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { tablesApi, type TableMetric } from '@/api/tables'
import { clustersApi, type Cluster } from '@/api/clusters'
import dayjs from 'dayjs'
import ScanProgressDialog from '@/components/ScanProgressDialog.vue'

// 数据
const clusters = ref<Cluster[]>([])
const tableMetrics = ref<TableMetric[]>([])
const selectedCluster = ref<number | null>(null)
const databases = ref<string[]>([])
const selectedDatabase = ref<string | ''>('')
const loading = ref(false)
const strictReal = ref(true)
const showProgress = ref(false)
const currentTaskId = ref<string | null>(null)
const maxPerDb = ref<number>(20)

// 方法
const loadClusters = async () => {
  try {
    clusters.value = await clustersApi.list()
    if (clusters.value.length > 0 && !selectedCluster.value) {
      selectedCluster.value = clusters.value[0].id
    }
  } catch (error) {
    console.error('Failed to load clusters:', error)
  }
}

const loadTableMetrics = async () => {
  if (!selectedCluster.value) return
  
  loading.value = true
  try {
    tableMetrics.value = await tablesApi.getMetrics(selectedCluster.value, selectedDatabase.value || undefined)
  } catch (error) {
    console.error('Failed to load table metrics:', error)
  } finally {
    loading.value = false
  }
}

const loadDatabases = async () => {
  if (!selectedCluster.value) return
  try {
    const list = await tablesApi.getDatabases(selectedCluster.value)
    // API 返回 { databases: string[] }
    databases.value = Array.isArray((list as any).databases) ? (list as any).databases : (list as any)
    if (databases.value.length && !selectedDatabase.value) {
      selectedDatabase.value = databases.value[0]
    }
  } catch (error) {
    console.error('Failed to load databases:', error)
  }
}

const triggerScan = async () => {
  if (!selectedCluster.value) { ElMessage.warning('请先选择集群'); return }
  if (!selectedDatabase.value) { ElMessage.warning('请先选择数据库'); return }
  
  try {
    await tablesApi.triggerScan(selectedCluster.value, selectedDatabase.value, undefined, strictReal.value)
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
  if (!selectedCluster.value) { ElMessage.warning('请先选择集群'); return }
  try {
    const res = await tablesApi.scanAllDatabases(selectedCluster.value, strictReal.value, maxPerDb.value)
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

const createMergeTask = (table: TableMetric) => {
  // TODO: 实现创建合并任务的逻辑
  ElMessage.info(`准备为表 ${table.database_name}.${table.table_name} 创建合并任务`)
}

// 归档表
const archiveTable = async (table: TableMetric) => {
  try {
    // 确认对话框
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
    const response = await tablesApi.archiveTable(selectedCluster.value, table.database_name, table.table_name, true)

    ElMessage.success(`表 ${table.database_name}.${table.table_name} 归档成功`)

    // 更新表状态
    table.archive_status = 'archived'
    table.archive_location = response.archive_result.archive_location
    table.archived_at = response.archive_result.archived_at

  } catch (error) {
    if (error !== 'cancel') {
      console.error('归档表失败:', error)
      ElMessage.error('归档表失败: ' + (error.message || error))
    }
  } finally {
    table.archiving = false
  }
}

// 恢复表
const restoreTable = async (table: TableMetric) => {
  try {
    // 确认对话框
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
    const response = await tablesApi.restoreTable(selectedCluster.value, table.database_name, table.table_name)

    ElMessage.success(`表 ${table.database_name}.${table.table_name} 恢复成功`)

    // 更新表状态
    table.archive_status = 'active'
    table.archive_location = null
    table.archived_at = null

  } catch (error) {
    if (error !== 'cancel') {
      console.error('恢复表失败:', error)
      ElMessage.error('恢复表失败: ' + (error.message || error))
    }
  } finally {
    table.restoring = false
  }
}

// 触发冷数据扫描
const triggerColdDataScan = async () => {
  if (!selectedCluster.value) {
    ElMessage.warning('请先选择集群')
    return
  }

  try {
    loading.value = true
    ElMessage.info('正在扫描冷数据...')

    const response = await tablesApi.scanColdData(
      selectedCluster.value,
      90, // 默认90天阈值
      selectedDatabase.value || undefined
    )

    ElMessage.success(`冷数据扫描完成！发现 ${response.scan_result?.cold_tables_found || 0} 个冷数据表`)

    // 刷新表格数据
    await loadTableMetrics()

  } catch (error) {
    console.error('冷数据扫描失败:', error)
    ElMessage.error('冷数据扫描失败')
  } finally {
    loading.value = false
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
watch(selectedCluster, () => {
  if (selectedCluster.value) {
    selectedDatabase.value = ''
    databases.value = []
    loadDatabases().then(() => loadTableMetrics())
  }
})

// 监听数据库变化
watch(selectedDatabase, () => {
  if (selectedCluster.value) {
    loadTableMetrics()
  }
})

onMounted(() => {
  loadClusters()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
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
</style>
