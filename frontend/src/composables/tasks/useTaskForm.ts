import { ref, computed, watch } from 'vue'
import type { Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { tasksApi, type MergeTaskCreate } from '@/api/tasks'
import { useMonitoringStore } from '@/stores/monitoring'

/**
 * 任务表单和分区处理
 */
export function useTaskForm() {
  const monitoringStore = useMonitoringStore()

  // 表单状态
  const showCreateDialog = ref(false)
  const taskFormRef = ref()

  const taskForm = ref<MergeTaskCreate>({
    cluster_id: 0,
    task_name: '',
    table_name: '',
    database_name: '',
    partition_filter: '',
    merge_strategy: 'safe_merge',
    target_storage_format: null,
    target_compression: 'KEEP'
  })

  const taskRules = {
    cluster_id: [{ required: true, message: '请选择集群', trigger: 'change' }],
    task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
    database_name: [{ required: true, message: '请输入数据库名', trigger: 'blur' }],
    table_name: [{ required: true, message: '请输入表名', trigger: 'blur' }]
  }

  // 分区相关
  const tableInfo = ref<any>(null)
  const partitions = ref<any[]>([])
  const selectedPartitions = ref<string[]>([])
  const partitionsLoading = ref(false)

  // 存储格式和压缩选项
  const storageFormatOptions = [
    { label: '保持原格式', value: null },
    { label: 'Parquet', value: 'PARQUET' },
    { label: 'ORC', value: 'ORC' },
    { label: 'TextFile', value: 'TEXTFILE' },
    { label: 'RCFile', value: 'RCFILE' },
    { label: 'Avro', value: 'AVRO' }
  ]

  const compressionOptions = [
    { label: '保持原压缩', value: 'KEEP' },
    { label: 'Snappy', value: 'SNAPPY' },
    { label: 'Gzip', value: 'GZIP' },
    { label: 'LZ4', value: 'LZ4' },
    { label: '不压缩', value: 'NONE' }
  ]

  // 计算属性
  const disableFormatSelection = computed(() => {
    const hasPartitionFilter =
      !!taskForm.value.partition_filter || selectedPartitions.value.length > 0
    return taskForm.value.merge_strategy !== 'safe_merge' || hasPartitionFilter
  })

  const disableCompressionSelection = computed(() => disableFormatSelection.value)

  const tableFormatLabel = computed(() => {
    if (!tableInfo.value) return '未知'
    return tableInfo.value.storage_format || '未知'
  })

  const tableCompressionLabel = computed(() => {
    if (!tableInfo.value) return '默认'
    const raw = (tableInfo.value.current_compression || '').toUpperCase()
    if (!raw || raw === 'DEFAULT') return '默认'
    return raw
  })

  // 监听集群变化
  watch(
    () => monitoringStore.settings.selectedCluster,
    clusterId => {
      taskForm.value.cluster_id = clusterId || 0
    }
  )

  // 监听合并策略变化
  watch(
    () => taskForm.value.merge_strategy,
    strategy => {
      if (strategy !== 'safe_merge') {
        taskForm.value.target_storage_format = null
        taskForm.value.target_compression = 'KEEP'
      }
    }
  )

  // 监听分区过滤器变化
  watch(
    () => [taskForm.value.partition_filter, selectedPartitions.value.length],
    () => {
      if (disableFormatSelection.value) {
        taskForm.value.target_storage_format = null
        taskForm.value.target_compression = 'KEEP'
      }
    }
  )

  /**
   * 检查表分区信息
   */
  const checkTablePartitions = async () => {
    if (!taskForm.value.cluster_id || !taskForm.value.database_name || !taskForm.value.table_name) {
      return
    }

    try {
      tableInfo.value = await tasksApi.getTableInfo(
        taskForm.value.cluster_id,
        taskForm.value.database_name,
        taskForm.value.table_name
      )
      partitions.value = []
      selectedPartitions.value = []
    } catch (error) {
      console.error('Failed to get table info:', error)
      tableInfo.value = null
    }
  }

  /**
   * 加载分区列表
   */
  const loadPartitions = async () => {
    if (!taskForm.value.cluster_id || !taskForm.value.database_name || !taskForm.value.table_name) {
      ElMessage.warning('请先选择集群、数据库和表名')
      return
    }

    partitionsLoading.value = true
    try {
      const response = await tasksApi.getTablePartitions(
        taskForm.value.cluster_id,
        taskForm.value.database_name,
        taskForm.value.table_name
      )
      partitions.value = response.partitions || []
      selectedPartitions.value = []
    } catch (error) {
      console.error('Failed to load partitions:', error)
      ElMessage.error('加载分区列表失败')
    } finally {
      partitionsLoading.value = false
    }
  }

  /**
   * 创建任务
   */
  const createTask = async (onSuccess: () => void) => {
    try {
      await taskFormRef.value.validate()

      const taskData = { ...taskForm.value }

      if (!taskData.target_storage_format) {
        delete taskData.target_storage_format
      } else {
        taskData.target_storage_format = taskData.target_storage_format.toUpperCase() as MergeTaskCreate['target_storage_format']
      }
      if (taskData.target_compression) {
        taskData.target_compression = taskData.target_compression.toUpperCase() as MergeTaskCreate['target_compression']
      }

      // 处理分区选择
      if (tableInfo.value?.is_partitioned && selectedPartitions.value.length > 0) {
        const partitionFilters = selectedPartitions.value.map(partition => `(${partition})`)
        taskData.partition_filter = partitionFilters.join(' OR ')
      }

      await tasksApi.create(taskData)

      ElMessage.success('任务创建成功')
      showCreateDialog.value = false
      resetTaskForm()
      onSuccess()
    } catch (error) {
      console.error('Failed to create task:', error)
      ElMessage.error('创建任务失败')
    }
  }

  /**
   * 重置表单
   */
  const resetTaskForm = () => {
    taskForm.value = {
      cluster_id: monitoringStore.settings.selectedCluster || 0,
      task_name: '',
      table_name: '',
      database_name: '',
      partition_filter: '',
      merge_strategy: 'safe_merge',
      target_storage_format: null,
      target_compression: 'KEEP'
    }
    tableInfo.value = null
    partitions.value = []
    selectedPartitions.value = []
  }

  return {
    // 状态
    showCreateDialog,
    taskFormRef,
    taskForm,
    taskRules,
    tableInfo,
    partitions,
    selectedPartitions,
    partitionsLoading,

    // 选项
    storageFormatOptions,
    compressionOptions,

    // 计算属性
    disableFormatSelection,
    disableCompressionSelection,
    tableFormatLabel,
    tableCompressionLabel,

    // 方法
    checkTablePartitions,
    loadPartitions,
    createTask,
    resetTaskForm
  }
}
