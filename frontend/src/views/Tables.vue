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
              :percentage="Math.round((row.small_files / row.total_files) * 100)"
              :color="getProgressColor((row.small_files / row.total_files) * 100)"
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
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="createMergeTask(row)">
              创建合并任务
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { tablesApi, type TableMetric } from '@/api/tables'
import { clustersApi, type Cluster } from '@/api/clusters'
import dayjs from 'dayjs'

// 数据
const clusters = ref<Cluster[]>([])
const tableMetrics = ref<TableMetric[]>([])
const selectedCluster = ref<number | null>(null)
const databases = ref<string[]>([])
const selectedDatabase = ref<string | ''>('')
const loading = ref(false)
const strictReal = ref(true)

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

const createMergeTask = (table: TableMetric) => {
  // TODO: 实现创建合并任务的逻辑
  ElMessage.info(`准备为表 ${table.database_name}.${table.table_name} 创建合并任务`)
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
