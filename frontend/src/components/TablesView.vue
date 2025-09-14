<template>
  <div class="tables-view">
    <div class="tables-header">
      <div class="search-filters">
        <el-input
          v-model="searchText"
          placeholder="搜索表名..."
          style="width: 300px"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        
        <el-select
          v-model="selectedDatabase"
          placeholder="选择数据库"
          clearable
          style="width: 200px"
        >
          <el-option
            v-for="db in databases"
            :key="db"
            :label="db"
            :value="db"
          />
        </el-select>
        
        <el-select
          v-model="filterStatus"
          placeholder="文件状态"
          clearable
          style="width: 150px"
        >
          <el-option label="所有表" value="" />
          <el-option label="小文件表" value="small_files" />
          <el-option label="正常表" value="normal" />
        </el-select>
      </div>
      
      <div class="action-buttons">
        <el-button @click="refreshTables">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="scanTables">
          <el-icon><Search /></el-icon>
          扫描表
        </el-button>
      </div>
    </div>

    <el-table
      :data="filteredTables"
      v-loading="loading"
      stripe
      style="width: 100%"
    >
      <el-table-column prop="database_name" label="数据库" width="120" />
      <el-table-column prop="table_name" label="表名" min-width="150" />
      <el-table-column prop="file_count" label="文件数" width="100" align="right" />
      <el-table-column prop="small_file_count" label="小文件数" width="120" align="right">
        <template #default="{ row }">
          <span :class="{ 'text-warning': row.small_file_count > 0 }">
            {{ row.small_file_count }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="分区数" width="100" align="right" sortable :sort-by="partitionCountSortKey">
        <template #default="{ row }">
          {{ row.is_partitioned ? (row.partition_count ?? 0) : -1 }}
        </template>
      </el-table-column>
      <el-table-column prop="total_size" label="总大小" width="120" align="right">
        <template #default="{ row }">
          {{ formatSize(row.total_size) }}
        </template>
      </el-table-column>
      <el-table-column prop="last_scan_time" label="最后扫描" width="180">
        <template #default="{ row }">
          {{ row.last_scan_time ? formatTime(row.last_scan_time) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button
            size="small"
            @click="viewTableDetail(row)"
          >
            详情
          </el-button>
          <el-button
            size="small"
            type="primary"
            @click="scanSingleTable(row)"
            :disabled="scanning"
          >
            扫描
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[20, 50, 100, 200]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { tablesApi } from '@/api/tables'
import dayjs from 'dayjs'

interface Props {
  clusterId: number
}

const props = defineProps<Props>()
const router = useRouter()

// Data
const tables = ref<any[]>([])
const databases = ref<string[]>([])
const loading = ref(false)
const scanning = ref(false)

// Filters
const searchText = ref('')
const selectedDatabase = ref('')
const filterStatus = ref('')

// Pagination
const currentPage = ref(1)
const pageSize = ref(50)
const total = ref(0)

// Computed
const filteredTables = computed(() => {
  let filtered = tables.value

  if (searchText.value) {
    filtered = filtered.filter(table =>
      table.table_name.toLowerCase().includes(searchText.value.toLowerCase())
    )
  }

  if (selectedDatabase.value) {
    filtered = filtered.filter(table => table.database_name === selectedDatabase.value)
  }

  if (filterStatus.value === 'small_files') {
    filtered = filtered.filter(table => table.small_file_count > 0)
  } else if (filterStatus.value === 'normal') {
    filtered = filtered.filter(table => table.small_file_count === 0)
  }

  return filtered
})

// Methods
const loadTables = async () => {
  loading.value = true
  try {
    // 使用非分页接口并映射字段以匹配当前UI
    const metrics = await tablesApi.getMetrics(props.clusterId)
    tables.value = metrics.map((m: any) => ({
      database_name: m.database_name,
      table_name: m.table_name,
      file_count: m.total_files,
      small_file_count: m.small_files,
      is_partitioned: !!m.is_partitioned,
      partition_count: m.partition_count ?? 0,
      total_size: m.total_size,
      last_scan_time: m.scan_time
    }))
    total.value = tables.value.length
  } catch (error) {
    console.error('Failed to load tables:', error)
    ElMessage.error('加载表列表失败')
  } finally {
    loading.value = false
  }
}

const loadDatabases = async () => {
  try {
    databases.value = await tablesApi.getDatabases(props.clusterId)
  } catch (error) {
    console.error('Failed to load databases:', error)
  }
}

const refreshTables = () => {
  loadTables()
}

const scanTables = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要扫描该集群的所有表吗？这可能需要较长时间。',
      '确认扫描',
      {
        confirmButtonText: '开始扫描',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    scanning.value = true
    await tablesApi.scanAllDatabases(props.clusterId)
    ElMessage.success('已开始扫描，请稍后查看结果')
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to scan tables:', error)
      ElMessage.error('扫描启动失败')
    }
  } finally {
    scanning.value = false
  }
}

const scanSingleTable = async (table: any) => {
  scanning.value = true
  try {
    await tablesApi.scanTable(props.clusterId, table.database_name, table.table_name)
    ElMessage.success(`表 ${table.table_name} 扫描完成`)
    await loadTables()
  } catch (error) {
    console.error('Failed to scan table:', error)
    ElMessage.error('表扫描失败')
  } finally {
    scanning.value = false
  }
}

const viewTableDetail = (table: any) => {
  router.push({
    name: 'TableDetail',
    params: {
      clusterId: props.clusterId,
      database: table.database_name,
      tableName: table.table_name
    }
  })
}

// 排序键：分区数（未分区为 -1）
const partitionCountSortKey = (row: any): number => {
  return row && row.is_partitioned ? (row.partition_count ?? 0) : -1
}


const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  loadTables()
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  loadTables()
}

const formatSize = (bytes: number): string => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatTime = (time: string): string => {
  return dayjs(time).format('MM-DD HH:mm')
}

// Watch cluster changes
watch(() => props.clusterId, () => {
  loadTables()
  loadDatabases()
}, { immediate: true })

onMounted(() => {
  loadTables()
  loadDatabases()
})
</script>

<style scoped>
.tables-view {
  height: 100%;
}

.tables-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 15px;
}

.search-filters {
  display: flex;
  gap: 15px;
  align-items: center;
  flex-wrap: wrap;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.text-warning {
  color: #e6a23c;
  font-weight: bold;
}

.pagination-wrapper {
  margin-top: 20px;
  text-align: center;
}

@media (max-width: 768px) {
  .tables-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-filters {
    justify-content: center;
  }
  
  .action-buttons {
    justify-content: center;
  }
}
</style>
