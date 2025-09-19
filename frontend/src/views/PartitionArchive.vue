<template>
  <div class="partition-archive-page">
    <div class="page-header">
      <h1 class="page-title">分区归档管理</h1>
      <p class="page-description">管理分区级别的冷数据归档，提供精细化的存储生命周期管理</p>
    </div>

    <!-- 统计概览 -->
    <div class="statistics-overview">
      <el-card class="stats-card">
        <template #header>
          <div class="card-header">
            <span>归档统计概览</span>
            <el-button @click="refreshStatistics" :loading="statisticsLoading" size="small" type="primary">
              刷新
            </el-button>
          </div>
        </template>
        <div v-if="statisticsLoading" class="loading-container">
          <el-skeleton :rows="3" animated />
        </div>
        <div v-else-if="statistics" class="stats-grid">
          <div class="stat-item">
            <div class="stat-value">{{ formatNumber(statistics.statistics.total_partitions) }}</div>
            <div class="stat-label">总分区数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ formatNumber(statistics.statistics.archived_partitions) }}</div>
            <div class="stat-label">已归档分区</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ statistics.statistics.archive_ratio.toFixed(1) }}%</div>
            <div class="stat-label">归档比例</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ formatFileSize(statistics.statistics.total_archived_size) }}</div>
            <div class="stat-label">归档数据量</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 主要功能区域 -->
    <el-tabs v-model="activeTab" class="archive-tabs">
      <!-- 冷数据扫描 -->
      <el-tab-pane label="冷数据扫描" name="scan">
        <div class="tab-content">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>扫描冷数据分区</span>
                <el-button @click="performColdScan" :loading="scanLoading" type="primary">
                  开始扫描
                </el-button>
              </div>
            </template>

            <!-- 扫描参数 -->
            <div class="scan-params">
              <el-form :model="scanParams" label-width="120px" size="small" inline>
                <el-form-item label="冷数据阈值">
                  <el-input-number
                    v-model="scanParams.cold_days_threshold"
                    :min="1"
                    :max="999"
                    controls-position="right"
                    style="width: 120px"
                  />
                  <span class="param-unit">天</span>
                </el-form-item>
                <el-form-item label="数据库名">
                  <el-input
                    v-model="scanParams.database_name"
                    placeholder="可选，留空扫描所有"
                    style="width: 200px"
                  />
                </el-form-item>
                <el-form-item label="表名">
                  <el-input
                    v-model="scanParams.table_name"
                    placeholder="可选，留空扫描所有"
                    style="width: 200px"
                  />
                </el-form-item>
                <el-form-item label="最小分区大小">
                  <el-input-number
                    v-model="scanParams.min_partition_size"
                    :min="0"
                    controls-position="right"
                    style="width: 150px"
                  />
                  <span class="param-unit">字节</span>
                </el-form-item>
              </el-form>
            </div>

            <!-- 扫描结果 -->
            <div v-if="scanResult" class="scan-result">
              <el-alert
                :title="`扫描完成：发现 ${scanResult.cold_partitions_found} 个冷数据分区`"
                type="success"
                :closable="false"
                show-icon
              />
              <div class="result-stats">
                <span>扫描分区数：{{ scanResult.total_partitions_scanned }}</span>
                <span>更新记录数：{{ scanResult.partitions_updated }}</span>
                <span>扫描时间：{{ formatDateTime(scanResult.scan_timestamp) }}</span>
              </div>
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 冷分区管理 -->
      <el-tab-pane label="冷分区管理" name="cold">
        <div class="tab-content">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>冷数据分区列表</span>
                <div class="header-actions">
                  <el-select v-model="coldParams.coldness_level" @change="loadColdPartitions" size="small">
                    <el-option label="极冷（6月以上）" value="very_cold" />
                    <el-option label="冷数据（3-6月）" value="cold" />
                    <el-option label="温数据（3月内）" value="warm" />
                  </el-select>
                  <el-button @click="loadColdPartitions" :loading="coldLoading" size="small">
                    刷新
                  </el-button>
                  <el-button
                    @click="batchArchiveSelected"
                    :disabled="selectedColdPartitions.length === 0"
                    :loading="batchArchiving"
                    type="primary"
                    size="small"
                  >
                    批量归档 ({{ selectedColdPartitions.length }})
                  </el-button>
                </div>
              </div>
            </template>

            <el-table
              :data="coldPartitions"
              v-loading="coldLoading"
              @selection-change="handleColdSelectionChange"
              style="width: 100%"
            >
              <el-table-column type="selection" width="55" />
              <el-table-column prop="database_name" label="数据库" width="150" />
              <el-table-column prop="table_name" label="表名" width="200" />
              <el-table-column prop="partition_name" label="分区名" min-width="200" />
              <el-table-column label="距上次访问" width="120">
                <template #default="{ row }">
                  {{ row.days_since_access }} 天
                </template>
              </el-table-column>
              <el-table-column label="分区大小" width="120">
                <template #default="{ row }">
                  {{ formatFileSize(row.partition_size) }}
                </template>
              </el-table-column>
              <el-table-column label="最后访问时间" width="180">
                <template #default="{ row }">
                  {{ formatDateTime(row.last_access_time) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button
                    @click="archiveSinglePartition(row)"
                    :loading="archivingPartitions[`${row.database_name}.${row.table_name}.${row.partition_name}`]"
                    type="primary"
                    size="small"
                  >
                    归档
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 已归档分区 -->
      <el-tab-pane label="已归档分区" name="archived">
        <div class="tab-content">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>已归档分区列表</span>
                <el-button @click="loadArchivedPartitions" :loading="archivedLoading" size="small">
                  刷新
                </el-button>
              </div>
            </template>

            <el-table :data="archivedPartitions" v-loading="archivedLoading" style="width: 100%">
              <el-table-column prop="database_name" label="数据库" width="150" />
              <el-table-column prop="table_name" label="表名" width="200" />
              <el-table-column prop="partition_name" label="分区名" min-width="200" />
              <el-table-column label="归档时间" width="180">
                <template #default="{ row }">
                  {{ formatDateTime(row.archived_at) }}
                </template>
              </el-table-column>
              <el-table-column label="归档大小" width="120">
                <template #default="{ row }">
                  {{ formatFileSize(row.total_size) }}
                </template>
              </el-table-column>
              <el-table-column prop="archive_location" label="归档位置" min-width="300" show-overflow-tooltip />
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button
                    @click="restoreSinglePartition(row)"
                    :loading="restoringPartitions[`${row.database_name}.${row.table_name}.${row.partition_name}`]"
                    type="warning"
                    size="small"
                  >
                    恢复
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 自动归档策略 -->
      <el-tab-pane label="自动归档" name="auto">
        <div class="tab-content">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>自动归档策略</span>
                <el-button @click="executeAutoArchive" :loading="autoArchiving" type="primary">
                  执行自动归档
                </el-button>
              </div>
            </template>

            <!-- 策略配置 -->
            <div class="auto-params">
              <el-form :model="autoParams" label-width="140px" size="small">
                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="冷数据阈值">
                      <el-input-number
                        v-model="autoParams.cold_days_threshold"
                        :min="1"
                        :max="999"
                        controls-position="right"
                        style="width: 150px"
                      />
                      <span class="param-unit">天</span>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="最小分区大小">
                      <el-input-number
                        v-model="autoParams.min_partition_size"
                        :min="0"
                        controls-position="right"
                        style="width: 150px"
                      />
                      <span class="param-unit">字节</span>
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="批量归档上限">
                      <el-input-number
                        v-model="autoParams.max_partitions_per_batch"
                        :min="1"
                        :max="1000"
                        controls-position="right"
                        style="width: 150px"
                      />
                      <span class="param-unit">个</span>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="测试模式">
                      <el-switch v-model="autoParams.dry_run" />
                      <span class="param-hint">（测试模式不会实际执行归档）</span>
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="20">
                  <el-col :span="12">
                    <el-form-item label="指定数据库">
                      <el-input
                        v-model="autoParams.database_name"
                        placeholder="可选，留空则处理所有数据库"
                        style="width: 200px"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="指定表名">
                      <el-input
                        v-model="autoParams.table_name"
                        placeholder="可选，留空则处理所有表"
                        style="width: 200px"
                      />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
            </div>

            <!-- 自动归档结果 -->
            <div v-if="autoArchiveResult" class="auto-result">
              <el-alert
                :title="`自动归档${autoParams.dry_run ? '测试' : ''}完成：成功归档 ${autoArchiveResult.successful_archives} 个分区`"
                :type="autoArchiveResult.failed_archives > 0 ? 'warning' : 'success'"
                :closable="false"
                show-icon
              />
              <div class="result-details">
                <p>总处理分区数：{{ autoArchiveResult.total_partitions }}</p>
                <p>成功归档：{{ autoArchiveResult.successful_archives }}</p>
                <p>失败数量：{{ autoArchiveResult.failed_archives }}</p>
                <p>执行时间：{{ formatDateTime(autoArchiveResult.batch_timestamp) }}</p>
              </div>

              <!-- 失败详情 -->
              <div v-if="autoArchiveResult.error_details.length > 0" class="error-details">
                <h4>失败详情：</h4>
                <ul>
                  <li v-for="error in autoArchiveResult.error_details" :key="error.partition_full_name">
                    {{ error.partition_full_name }}: {{ error.error }}
                  </li>
                </ul>
              </div>
            </div>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMonitoringStore } from '@/stores/monitoring'
import * as partitionArchiveApi from '@/api/partitionArchive'
import type {
  ColdPartition,
  ArchivedPartition,
  PartitionArchiveStatistics,
  ScanColdPartitionsRequest,
  ScanColdPartitionsResult,
  BatchArchiveRequest,
  BatchArchiveResult
} from '@/api/partitionArchive'

// Stores
const monitoringStore = useMonitoringStore()

// 当前选中的标签页
const activeTab = ref('scan')

// 统计数据
const statistics = ref<PartitionArchiveStatistics | null>(null)
const statisticsLoading = ref(false)

// 冷数据扫描
const scanParams = reactive<ScanColdPartitionsRequest>({
  cold_days_threshold: 90,
  database_name: '',
  table_name: '',
  min_partition_size: 0
})
const scanLoading = ref(false)
const scanResult = ref<ScanColdPartitionsResult | null>(null)

// 冷分区管理
const coldPartitions = ref<ColdPartition[]>([])
const coldLoading = ref(false)
const coldParams = reactive({
  coldness_level: 'cold' as 'very_cold' | 'cold' | 'warm'
})
const selectedColdPartitions = ref<ColdPartition[]>([])
const batchArchiving = ref(false)
const archivingPartitions = reactive<Record<string, boolean>>({})

// 已归档分区
const archivedPartitions = ref<ArchivedPartition[]>([])
const archivedLoading = ref(false)
const restoringPartitions = reactive<Record<string, boolean>>({})

// 自动归档
const autoParams = reactive({
  cold_days_threshold: 90,
  min_partition_size: 1024 * 1024, // 1MB
  max_partitions_per_batch: 50,
  database_name: '',
  table_name: '',
  dry_run: true
})
const autoArchiving = ref(false)
const autoArchiveResult = ref<BatchArchiveResult | null>(null)

// 计算属性
const selectedClusterId = computed(() => monitoringStore.selectedCluster?.id)

// 工具函数
const formatNumber = (num: number) => {
  return num.toLocaleString()
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDateTime = (dateStr: string | null) => {
  if (!dateStr) return '未知'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 刷新统计数据
const refreshStatistics = async () => {
  if (!selectedClusterId.value) return

  statisticsLoading.value = true
  try {
    const response = await partitionArchiveApi.getPartitionArchiveStatistics(selectedClusterId.value)
    statistics.value = response.data.statistics
  } catch (error) {
    console.error('Failed to load statistics:', error)
    ElMessage.error('加载统计数据失败')
  } finally {
    statisticsLoading.value = false
  }
}

// 执行冷数据扫描
const performColdScan = async () => {
  if (!selectedClusterId.value) return

  scanLoading.value = true
  try {
    const params = { ...scanParams }
    if (!params.database_name) delete params.database_name
    if (!params.table_name) delete params.table_name

    const response = await partitionArchiveApi.scanColdPartitions(selectedClusterId.value, params)
    scanResult.value = response.data
    ElMessage.success('冷数据扫描完成')

    // 如果当前在冷分区标签页，刷新数据
    if (activeTab.value === 'cold') {
      loadColdPartitions()
    }
  } catch (error: any) {
    console.error('Failed to scan cold partitions:', error)
    ElMessage.error(`扫描失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    scanLoading.value = false
  }
}

// 加载冷分区列表
const loadColdPartitions = async () => {
  if (!selectedClusterId.value) return

  coldLoading.value = true
  try {
    const response = await partitionArchiveApi.getColdPartitionsList(
      selectedClusterId.value,
      coldParams.coldness_level
    )
    coldPartitions.value = response.data
  } catch (error) {
    console.error('Failed to load cold partitions:', error)
    ElMessage.error('加载冷分区列表失败')
  } finally {
    coldLoading.value = false
  }
}

// 处理冷分区选择变化
const handleColdSelectionChange = (selections: ColdPartition[]) => {
  selectedColdPartitions.value = selections
}

// 归档单个分区
const archiveSinglePartition = async (partition: ColdPartition) => {
  if (!selectedClusterId.value) return

  const partitionKey = `${partition.database_name}.${partition.table_name}.${partition.partition_name}`

  try {
    await ElMessageBox.confirm(
      `确定要归档分区 ${partitionKey} 吗？归档后数据将移动到归档存储位置。`,
      '确认归档',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    archivingPartitions[partitionKey] = true
    await partitionArchiveApi.archivePartition(
      selectedClusterId.value,
      partition.database_name,
      partition.table_name,
      partition.partition_name
    )

    ElMessage.success('分区归档成功')
    loadColdPartitions()
    refreshStatistics()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to archive partition:', error)
      ElMessage.error(`归档失败: ${error.response?.data?.detail || error.message}`)
    }
  } finally {
    archivingPartitions[partitionKey] = false
  }
}

// 批量归档选中分区
const batchArchiveSelected = async () => {
  if (!selectedClusterId.value || selectedColdPartitions.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要归档选中的 ${selectedColdPartitions.value.length} 个分区吗？`,
      '确认批量归档',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    batchArchiving.value = true
    const request: BatchArchiveRequest = {
      partitions: selectedColdPartitions.value.map(p => ({
        database_name: p.database_name,
        table_name: p.table_name,
        partition_name: p.partition_name
      }))
    }

    const response = await partitionArchiveApi.batchArchivePartitions(selectedClusterId.value, request)
    const result = response.data

    ElMessage.success(`批量归档完成：成功 ${result.successful_archives} 个，失败 ${result.failed_archives} 个`)
    loadColdPartitions()
    refreshStatistics()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to batch archive:', error)
      ElMessage.error(`批量归档失败: ${error.response?.data?.detail || error.message}`)
    }
  } finally {
    batchArchiving.value = false
  }
}

// 加载已归档分区
const loadArchivedPartitions = async () => {
  if (!selectedClusterId.value) return

  archivedLoading.value = true
  try {
    const response = await partitionArchiveApi.getArchivedPartitions(selectedClusterId.value)
    archivedPartitions.value = response.data.archived_partitions
  } catch (error) {
    console.error('Failed to load archived partitions:', error)
    ElMessage.error('加载已归档分区列表失败')
  } finally {
    archivedLoading.value = false
  }
}

// 恢复单个分区
const restoreSinglePartition = async (partition: ArchivedPartition) => {
  if (!selectedClusterId.value) return

  const partitionKey = `${partition.database_name}.${partition.table_name}.${partition.partition_name}`

  try {
    await ElMessageBox.confirm(
      `确定要恢复分区 ${partitionKey} 吗？数据将从归档位置移动回原始位置。`,
      '确认恢复',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    restoringPartitions[partitionKey] = true
    await partitionArchiveApi.restorePartition(
      selectedClusterId.value,
      partition.database_name,
      partition.table_name,
      partition.partition_name
    )

    ElMessage.success('分区恢复成功')
    loadArchivedPartitions()
    refreshStatistics()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to restore partition:', error)
      ElMessage.error(`恢复失败: ${error.response?.data?.detail || error.message}`)
    }
  } finally {
    restoringPartitions[partitionKey] = false
  }
}

// 执行自动归档
const executeAutoArchive = async () => {
  if (!selectedClusterId.value) return

  try {
    await ElMessageBox.confirm(
      `确定要执行自动归档${autoParams.dry_run ? '测试' : ''}吗？`,
      '确认自动归档',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    autoArchiving.value = true
    const params = { ...autoParams }
    if (!params.database_name) delete params.database_name
    if (!params.table_name) delete params.table_name

    const response = await partitionArchiveApi.autoArchiveByPolicy(selectedClusterId.value, params)
    autoArchiveResult.value = response.data

    ElMessage.success(`自动归档${autoParams.dry_run ? '测试' : ''}完成`)
    if (!autoParams.dry_run) {
      refreshStatistics()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to auto archive:', error)
      ElMessage.error(`自动归档失败: ${error.response?.data?.detail || error.message}`)
    }
  } finally {
    autoArchiving.value = false
  }
}

// 组件挂载时加载数据
onMounted(() => {
  refreshStatistics()
})
</script>

<style scoped>
.partition-archive-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.page-description {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.statistics-overview {
  margin-bottom: 20px;
}

.stats-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.loading-container {
  padding: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.archive-tabs {
  background: white;
}

.tab-content {
  padding: 0;
}

.scan-params {
  margin-bottom: 20px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 4px;
}

.param-unit {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}

.param-hint {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}

.scan-result {
  margin-top: 20px;
}

.result-stats {
  margin-top: 10px;
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: #606266;
}

.auto-params {
  margin-bottom: 20px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 4px;
}

.auto-result {
  margin-top: 20px;
}

.result-details {
  margin-top: 10px;
  font-size: 14px;
  color: #606266;
}

.result-details p {
  margin: 4px 0;
}

.error-details {
  margin-top: 15px;
  padding: 15px;
  background: #fef0f0;
  border: 1px solid #fbc4c4;
  border-radius: 4px;
}

.error-details h4 {
  margin: 0 0 10px 0;
  color: #f56c6c;
  font-size: 14px;
}

.error-details ul {
  margin: 0;
  padding-left: 20px;
}

.error-details li {
  margin-bottom: 5px;
  color: #f56c6c;
  font-size: 12px;
}
</style>