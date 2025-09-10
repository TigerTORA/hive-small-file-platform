<template>
  <div class="table-detail">
    <div class="breadcrumb-container">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/dashboard' }">监控仪表板</el-breadcrumb-item>
        <el-breadcrumb-item :to="{ path: '/tables' }">表管理</el-breadcrumb-item>
        <el-breadcrumb-item>{{ clusterId }}.{{ database }}.{{ tableName }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <el-card class="table-info-card">
      <template #header>
        <div class="card-header">
          <span>表详情</span>
          <div class="header-actions">
            <el-button type="primary" @click="refreshTableInfo" :loading="loading">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button 
              type="success" 
              @click="showMergeDialog = true" 
              :disabled="!tableMetric || tableMetric.small_files === 0"
            >
              <el-icon><Operation /></el-icon>
              一键合并
            </el-button>
          </div>
        </div>
      </template>

      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="6" animated />
      </div>

      <div v-else-if="tableMetric" class="table-info-content">
        <!-- 基本信息 -->
        <div class="info-section">
          <h3>基本信息</h3>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic title="表名" :value="tableMetric.table_name" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="数据库" :value="tableMetric.database_name" />
            </el-col>
            <el-col :span="6">
              <div class="statistic-item">
                <div class="statistic-title">表类型</div>
                <el-tag :type="getTableTypeColor(tableMetric.table_type)" size="default">
                  {{ formatTableType(tableMetric.table_type) }}
                </el-tag>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="statistic-item">
                <div class="statistic-title">存储格式</div>
                <el-tag type="info" size="default">
                  {{ tableMetric.storage_format || 'UNKNOWN' }}
                </el-tag>
              </div>
            </el-col>
          </el-row>
          
          <el-row :gutter="20" style="margin-top: 16px;">
            <el-col :span="6">
              <div class="statistic-item">
                <div class="statistic-title">分区表</div>
                <el-tag :type="tableMetric.is_partitioned ? 'success' : 'info'" size="default">
                  {{ tableMetric.is_partitioned ? '是' : '否' }}
                </el-tag>
              </div>
            </el-col>
            <el-col :span="6" v-if="tableMetric.is_partitioned">
              <el-statistic title="分区数量" :value="tableMetric.partition_count" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="表拥有者" :value="tableMetric.table_owner || 'Unknown'" />
            </el-col>
            <el-col :span="6" v-if="tableMetric.table_create_time">
              <el-statistic title="创建时间" :value="formatTime(tableMetric.table_create_time)" />
            </el-col>
          </el-row>
        </div>

        <!-- 文件统计 -->
        <div class="info-section">
          <h3>文件统计</h3>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic title="总文件数" :value="tableMetric.total_files" />
            </el-col>
            <el-col :span="6">
              <el-statistic 
                title="小文件数" 
                :value="tableMetric.small_files" 
                :value-style="{ color: tableMetric.small_files > 0 ? '#f56c6c' : '#67c23a' }"
              />
            </el-col>
            <el-col :span="6">
              <div class="statistic-item">
                <div class="statistic-title">小文件占比</div>
                <el-progress
                  :percentage="Math.round((tableMetric.small_files / tableMetric.total_files) * 100)"
                  :color="getProgressColor((tableMetric.small_files / tableMetric.total_files) * 100)"
                  :show-text="true"
                  style="width: 120px;"
                />
              </div>
            </el-col>
            <el-col :span="6">
              <el-statistic title="总大小" :value="formatSize(tableMetric.total_size)" />
            </el-col>
          </el-row>
        </div>

        <!-- 扫描信息 -->
        <div class="info-section">
          <h3>扫描信息</h3>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-statistic title="最后扫描时间" :value="formatTime(tableMetric.scan_time)" />
            </el-col>
            <el-col :span="12">
              <div class="statistic-item">
                <div class="statistic-title">扫描状态</div>
                <el-tag type="success" size="default">已完成</el-tag>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 优化建议 -->
        <div class="info-section">
          <h3>智能优化建议</h3>
          <div class="recommendations">
            <!-- 小文件问题 -->
            <el-alert
              v-if="tableMetric.small_files > 0"
              :title="`🚨 小文件问题：检测到 ${tableMetric.small_files} 个小文件（${getSmallFileRatio()}%）`"
              :type="getSmallFileSeverity()"
              :closable="false"
              style="margin-bottom: 12px;"
            >
              <template #default>
                <div class="recommendation-content">
                  <p><strong>影响分析：</strong>{{ getSmallFileImpact() }}</p>
                  <p><strong>推荐策略：</strong></p>
                  <ul>
                    <li v-for="suggestion in getSmallFileSuggestions()" :key="suggestion">
                      {{ suggestion }}
                    </li>
                  </ul>
                </div>
              </template>
            </el-alert>

            <!-- 存储格式建议 -->
            <el-alert
              v-if="getStorageFormatAdvice()"
              title="💾 存储格式优化"
              type="info"
              :closable="false"
              style="margin-bottom: 12px;"
            >
              <template #default>
                <div class="recommendation-content">
                  <p>{{ getStorageFormatAdvice() }}</p>
                </div>
              </template>
            </el-alert>

            <!-- 分区优化建议 -->
            <el-alert
              v-if="getPartitionAdvice()"
              title="🗂️ 分区优化"
              type="info"
              :closable="false"
              style="margin-bottom: 12px;"
            >
              <template #default>
                <div class="recommendation-content">
                  <p>{{ getPartitionAdvice() }}</p>
                </div>
              </template>
            </el-alert>

            <!-- 健康状态 -->
            <el-alert
              v-if="tableMetric.small_files === 0 && tableMetric.total_files > 0"
              title="✅ 表状态健康"
              type="success"
              :closable="false"
            >
              <template #default>
                <p>当前表文件结构良好，无小文件问题。继续保持良好的数据管理实践！</p>
              </template>
            </el-alert>
          </div>
        </div>
      </div>

      <div v-else class="no-data">
        <el-empty description="未找到表信息" />
      </div>
    </el-card>

    <!-- 合并任务对话框 -->
    <el-dialog v-model="showMergeDialog" title="创建合并任务" width="500px">
      <el-form :model="mergeForm" :rules="mergeRules" ref="mergeFormRef" label-width="120px">
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="mergeForm.task_name" placeholder="自动生成任务名称" />
        </el-form-item>
        <el-form-item label="合并策略">
          <el-radio-group v-model="mergeForm.merge_strategy">
            <el-radio label="safe_merge">安全合并 (推荐)</el-radio>
            <el-radio label="concatenate">文件合并</el-radio>
            <el-radio label="insert_overwrite">重写插入</el-radio>
          </el-radio-group>
          <div style="margin-top: 4px; font-size: 12px; color: #909399;">
            安全合并使用临时表+重命名策略，确保零停机时间
          </div>
        </el-form-item>
        <el-form-item label="目标文件大小">
          <el-input-number
            v-model="mergeForm.target_file_size"
            :min="1024 * 1024"
            :step="64 * 1024 * 1024"
            placeholder="字节"
          />
          <span style="margin-left: 8px; color: #909399;">字节（可选）</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showMergeDialog = false">取消</el-button>
          <el-button type="primary" @click="createMergeTask" :loading="creating">创建并执行</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { tablesApi, type TableMetric } from '@/api/tables'
import { tasksApi, type MergeTaskCreate } from '@/api/tasks'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const clusterId = computed(() => Number(route.params.clusterId))
const database = computed(() => String(route.params.database))
const tableName = computed(() => String(route.params.tableName))

const loading = ref(false)
const creating = ref(false)
const showMergeDialog = ref(false)
const tableMetric = ref<TableMetric | null>(null)

const mergeForm = ref<MergeTaskCreate>({
  cluster_id: 0,
  task_name: '',
  table_name: '',
  database_name: '',
  partition_filter: '',
  merge_strategy: 'safe_merge'
})

const mergeRules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }]
}

const mergeFormRef = ref()

const loadTableInfo = async () => {
  loading.value = true
  try {
    const metrics = await tablesApi.getMetrics(clusterId.value)
    tableMetric.value = metrics.find(
      (metric: TableMetric) => 
        metric.database_name === database.value && 
        metric.table_name === tableName.value
    ) || null

    if (tableMetric.value) {
      mergeForm.value = {
        cluster_id: clusterId.value,
        task_name: `merge_${database.value}_${tableName.value}_${Date.now()}`,
        table_name: tableName.value,
        database_name: database.value,
        partition_filter: '',
        merge_strategy: 'safe_merge'
      }
    }
  } catch (error) {
    console.error('Failed to load table info:', error)
    ElMessage.error('加载表信息失败')
  } finally {
    loading.value = false
  }
}

const refreshTableInfo = async () => {
  try {
    await tablesApi.triggerScan(clusterId.value)
    ElMessage.success('扫描任务已启动')
    setTimeout(() => {
      loadTableInfo()
    }, 2000)
  } catch (error) {
    console.error('Failed to trigger scan:', error)
    ElMessage.error('触发扫描失败')
  }
}

const createMergeTask = async () => {
  try {
    await mergeFormRef.value.validate()
    creating.value = true
    
    const task = await tasksApi.create(mergeForm.value)
    await tasksApi.execute(task.id)
    
    ElMessage.success('合并任务已创建并启动')
    showMergeDialog.value = false
    
    router.push('/tasks')
  } catch (error) {
    console.error('Failed to create merge task:', error)
    ElMessage.error('创建合并任务失败')
  } finally {
    creating.value = false
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
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const getProgressColor = (percentage: number): string => {
  if (percentage > 80) return '#f56c6c'
  if (percentage > 50) return '#e6a23c'
  if (percentage > 20) return '#1989fa'
  return '#67c23a'
}

const getTableTypeColor = (tableType: string): string => {
  switch (tableType) {
    case 'MANAGED_TABLE':
      return 'success'
    case 'EXTERNAL_TABLE':
      return 'warning'
    case 'VIEW':
      return 'info'
    default:
      return ''
  }
}

const formatTableType = (tableType: string): string => {
  switch (tableType) {
    case 'MANAGED_TABLE':
      return '托管表'
    case 'EXTERNAL_TABLE':
      return '外部表'
    case 'VIEW':
      return '视图'
    default:
      return tableType || '未知'
  }
}

const getSmallFileRatio = (): number => {
  if (!tableMetric.value || tableMetric.value.total_files === 0) return 0
  return Math.round((tableMetric.value.small_files / tableMetric.value.total_files) * 100)
}

const getSmallFileSeverity = (): string => {
  const ratio = getSmallFileRatio()
  if (ratio >= 80) return 'error'
  if (ratio >= 50) return 'warning'
  return 'info'
}

const getSmallFileImpact = (): string => {
  const ratio = getSmallFileRatio()
  if (ratio >= 80) return '严重影响查询性能，强烈建议立即进行文件合并优化'
  if (ratio >= 50) return '显著影响查询效率，建议尽快进行文件合并优化'
  if (ratio >= 20) return '轻微影响查询性能，建议安排文件合并任务'
  return '小文件数量较少，但仍建议定期进行文件整理'
}

const getSmallFileSuggestions = (): string[] => {
  if (!tableMetric.value) return []
  
  const suggestions = []
  const ratio = getSmallFileRatio()
  
  if (ratio >= 80) {
    suggestions.push('立即执行安全合并策略，可提升查询性能50%+')
    suggestions.push('考虑调整数据写入方式，避免产生更多小文件')
  } else if (ratio >= 50) {
    suggestions.push('使用安全合并策略进行文件合并')
    suggestions.push('建议在业务低峰期执行合并任务')
  } else {
    suggestions.push('可选择性进行文件合并优化')
    suggestions.push('监控后续数据写入，防止小文件累积')
  }
  
  if (tableMetric.value.is_partitioned) {
    suggestions.push('分区表可按分区逐步进行合并，降低对业务的影响')
  }
  
  if (tableMetric.value.storage_format === 'TEXT') {
    suggestions.push('考虑转换为 ORC 或 Parquet 格式以获得更好性能')
  }
  
  return suggestions
}

const getStorageFormatAdvice = (): string | null => {
  if (!tableMetric.value) return null
  
  const format = tableMetric.value.storage_format
  const totalSize = tableMetric.value.total_size
  
  if (format === 'TEXT') {
    if (totalSize > 100 * 1024 * 1024) { // > 100MB
      return `当前使用 TEXT 格式，建议转换为 ORC 或 Parquet 格式。预计可减少存储空间 30-50%，提升查询性能 2-5 倍。`
    }
    return `TEXT 格式适合小数据量，但不支持列式存储优化。考虑升级到 ORC 或 Parquet。`
  }
  
  if (format === 'SEQUENCE' || format === 'AVRO') {
    return `${format} 格式功能完整但性能不如 ORC/Parquet。建议评估转换到列式存储格式的可行性。`
  }
  
  if (format === 'ORC' || format === 'PARQUET') {
    return null // 已经是最优格式
  }
  
  return `建议评估当前 ${format} 格式是否为最佳选择，考虑 ORC 或 Parquet 格式的性能优势。`
}

const getPartitionAdvice = (): string | null => {
  if (!tableMetric.value) return null
  
  const { is_partitioned, partition_count, total_files, total_size } = tableMetric.value
  
  if (!is_partitioned) {
    if (total_size > 1024 * 1024 * 1024) { // > 1GB
      return '大表建议考虑分区策略，可显著提升查询性能。常用分区键：日期、地区、业务类型等。'
    }
    return null
  }
  
  if (partition_count > 10000) {
    return `分区数量过多（${partition_count}个），可能导致元数据压力。建议合并小分区或调整分区策略。`
  }
  
  if (partition_count > 0 && total_files / partition_count < 5) {
    return '平均每个分区文件数过少，建议合并小分区或调整数据写入策略。'
  }
  
  return null
}

onMounted(() => {
  loadTableInfo()
})
</script>

<style scoped>
.breadcrumb-container {
  margin-bottom: 20px;
}

.table-info-card {
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
}

.loading-container {
  padding: 20px;
}

.table-info-content {
  padding: 20px 0;
}

.info-section {
  margin-bottom: 32px;
}

.info-section h3 {
  margin-bottom: 16px;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.statistic-item {
  text-align: left;
}

.statistic-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.no-data {
  padding: 40px;
  text-align: center;
}

.dialog-footer {
  text-align: right;
}

:deep(.el-statistic__content) {
  font-size: 24px;
  font-weight: 600;
}

:deep(.el-statistic__title) {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

:deep(.el-alert ul) {
  margin: 8px 0 0 20px;
}

:deep(.el-alert li) {
  margin-bottom: 4px;
}

.recommendations {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recommendation-content {
  font-size: 14px;
  line-height: 1.5;
}

.recommendation-content p {
  margin: 8px 0;
}

.recommendation-content ul {
  margin: 8px 0 0 20px;
  padding-left: 0;
}

.recommendation-content li {
  margin-bottom: 6px;
  color: #606266;
}
</style>