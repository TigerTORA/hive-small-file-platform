<template>
  <div class="table-archive">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>文件归档</span>
          <div class="header-actions">
            <el-select v-model="selectedCluster" placeholder="选择集群" style="width: 200px; margin-right: 10px">
              <el-option v-for="c in clusters" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-select v-model="selectedDatabase" placeholder="选择数据库" style="width: 220px; margin-right: 10px" :disabled="!databases.length">
              <el-option v-for="db in databases" :key="db" :label="db" :value="db" />
            </el-select>
            <el-button @click="loadColdTables" type="primary" :disabled="!selectedCluster">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="冷数据表" name="cold">
          <div class="tab-tools">
            <el-input v-model="searchText" clearable placeholder="搜索表名..." style="width: 240px">
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <div style="flex: 1"></div>
            <el-input-number v-model="minDays" :min="0" :max="999" controls-position="right" style="width: 140px" />
            <span style="margin-left: 6px; color: #909399">最小未访问天数</span>
          </div>
          <el-table :data="filteredColdTables" v-loading="loadingCold" stripe>
            <el-table-column prop="database_name" label="数据库" width="140" />
            <el-table-column prop="table_name" label="表名" min-width="220" />
            <el-table-column label="未访问天数" width="120">
              <template #default="{ row }">{{ row.days_since_last_access || '-' }}</template>
            </el-table-column>
            <el-table-column label="上次访问" width="180">
              <template #default="{ row }">{{ formatTime(row.last_access_time) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.archive_status === 'archived'" type="danger" size="small">已归档</el-tag>
                <el-tag v-else type="primary" size="small">活跃中</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.archive_status !== 'archived'"
                  type="warning"
                  size="small"
                  @click="archiveTableRow(row)"
                  :loading="archivingKey === rowKey(row)"
                >
                  归档
                </el-button>
                <el-button
                  v-else
                  type="success"
                  size="small"
                  @click="restoreTableRow(row)"
                  :loading="restoringKey === rowKey(row)"
                >
                  恢复
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrapper" v-if="coldTotal > 0">
            <el-pagination
              v-model:current-page="coldPage"
              v-model:page-size="coldPageSize"
              :page-sizes="[20, 50, 100, 200]"
              layout="total, sizes, prev, pager, next, jumper"
              :total="coldTotal"
              @size-change="loadColdTables"
              @current-change="loadColdTables"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="已归档表" name="archived">
          <el-table :data="archivedTables" v-loading="loadingArchived" stripe>
            <el-table-column prop="database_name" label="数据库" width="140" />
            <el-table-column prop="table_name" label="表名" min-width="220" />
            <el-table-column label="归档时间" width="180">
              <template #default="{ row }">{{ formatTime(row.archived_at) }}</template>
            </el-table-column>
            <el-table-column prop="archive_location" label="归档位置" min-width="260" show-overflow-tooltip />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="restoreArchivedRow(row)" :loading="restoringKey === rowKey(row)">恢复</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrapper" v-if="archivedTotal > 0">
            <el-pagination
              v-model:current-page="archivedPage"
              v-model:page-size="archivedPageSize"
              :page-sizes="[20, 50, 100, 200]"
              layout="total, sizes, prev, pager, next, jumper"
              :total="archivedTotal"
              @size-change="loadArchivedTables"
              @current-change="loadArchivedTables"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
  import { ref, computed, onMounted, watch } from 'vue'
  import { ElMessage } from 'element-plus'
  import { Refresh, Search } from '@element-plus/icons-vue'
  import { clustersApi, type Cluster } from '@/api/clusters'
  import { tablesApi } from '@/api/tables'
  import dayjs from 'dayjs'

  // State
  const clusters = ref<Cluster[]>([])
  const selectedCluster = ref<number | null>(null)
  const databases = ref<string[]>([])
  const selectedDatabase = ref<string>('')

  const activeTab = ref<'cold' | 'archived'>('cold')
  const searchText = ref('')
  const minDays = ref(0)

  // Cold tables
  const loadingCold = ref(false)
  const coldTables = ref<any[]>([])
  const coldPage = ref(1)
  const coldPageSize = ref(50)
  const coldTotal = ref(0)

  // Archived tables
  const loadingArchived = ref(false)
  const archivedTables = ref<any[]>([])
  const archivedPage = ref(1)
  const archivedPageSize = ref(50)
  const archivedTotal = ref(0)

  // Row operation states
  const archivingKey = ref('')
  const restoringKey = ref('')

  const rowKey = (row: any) => `${row.database_name}.${row.table_name}`

  const filteredColdTables = computed(() => {
    if (!searchText.value) return coldTables.value
    const q = searchText.value.toLowerCase()
    return coldTables.value.filter((r: any) => `${r.database_name}.${r.table_name}`.toLowerCase().includes(q))
  })

  // Loaders
  const loadClusters = async () => {
    clusters.value = await clustersApi.list()
    if (clusters.value.length && !selectedCluster.value) {
      selectedCluster.value = clusters.value[0].id
    }
  }

  const loadDatabases = async () => {
    if (!selectedCluster.value) return
    const list = await tablesApi.getDatabases(selectedCluster.value)
    databases.value = Array.isArray((list as any).databases) ? (list as any).databases : (list as any)
    if (databases.value.length && !selectedDatabase.value) selectedDatabase.value = databases.value[0]
  }

  const loadColdTables = async () => {
    if (!selectedCluster.value) return
    loadingCold.value = true
    try {
      const res = await tablesApi.getColdDataList(selectedCluster.value, coldPage.value, coldPageSize.value)
      coldTables.value = (res.cold_tables || []).filter((t: any) => !selectedDatabase.value || t.database_name === selectedDatabase.value)
      coldTotal.value = res.pagination?.total_count || coldTables.value.length
    } catch (e) {
      console.error(e)
    } finally {
      loadingCold.value = false
    }
  }

  const loadArchivedTables = async () => {
    if (!selectedCluster.value) return
    loadingArchived.value = true
    try {
      const res = await tablesApi.getArchivedTables(selectedCluster.value, archivedPageSize.value)
      // API返回分页/列表结构，做兼容
      archivedTables.value = res.archived_tables || res.items || []
      archivedTotal.value = res.pagination?.total_count || archivedTables.value.length
    } catch (e) {
      console.error(e)
    } finally {
      loadingArchived.value = false
    }
  }

  // Actions
  const archiveTableRow = async (row: any) => {
    if (!selectedCluster.value) return
    try {
      archivingKey.value = rowKey(row)
      await tablesApi.archiveTable(selectedCluster.value, row.database_name, row.table_name, true)
      ElMessage.success(`已归档 ${row.database_name}.${row.table_name}`)
      await loadColdTables()
      await loadArchivedTables()
    } catch (e: any) {
      ElMessage.error(e?.message || '归档失败')
    } finally {
      archivingKey.value = ''
    }
  }

  const restoreTableRow = async (row: any) => {
    if (!selectedCluster.value) return
    try {
      restoringKey.value = rowKey(row)
      await tablesApi.restoreTable(selectedCluster.value, row.database_name, row.table_name)
      ElMessage.success(`已恢复 ${row.database_name}.${row.table_name}`)
      await loadColdTables()
      await loadArchivedTables()
    } catch (e: any) {
      ElMessage.error(e?.message || '恢复失败')
    } finally {
      restoringKey.value = ''
    }
  }

  const restoreArchivedRow = (row: any) => restoreTableRow(row)

  const formatTime = (time?: string | null) => (time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-')

  // Watchers
  watch(selectedCluster, async () => {
    selectedDatabase.value = ''
    databases.value = []
    await loadDatabases()
    await loadColdTables()
    await loadArchivedTables()
  })

  watch(selectedDatabase, () => {
    loadColdTables()
  })

  onMounted(async () => {
    await loadClusters()
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
  .tab-tools {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 10px 0 16px;
  }
  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }
</style>

