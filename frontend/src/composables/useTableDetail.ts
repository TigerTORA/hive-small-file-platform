import { ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { tablesApi, type TableMetric } from '@/api/tables'
import { FeatureManager } from '@/utils/feature-flags'

export const useTableDetail = (
  clusterId: Ref<number>,
  database: Ref<string>,
  tableName: Ref<string>
) => {
  const loading = ref(true)
  const tableMetric = ref<TableMetric | null>(null)
  const tableInfoExtra = ref<any | null>(null)
  const mergeSupported = ref(true)
  const unsupportedReason = ref('')

  const loadTableInfo = async (options: { skipLoading?: boolean } = {}) => {
    if (!options.skipLoading) {
      loading.value = true
    }
    try {
      const metrics = await tablesApi.getMetrics(clusterId.value, database.value)
      tableMetric.value =
        metrics.find(
          (metric: TableMetric) =>
            metric.database_name === database.value && metric.table_name === tableName.value
        ) || null

      if (tableMetric.value) {
        try {
          const info = await tablesApi.getCachedTableInfo(
            clusterId.value,
            database.value,
            tableName.value
          )
          tableInfoExtra.value = info || null

          mergeSupported.value = info?.merge_supported !== false
          unsupportedReason.value =
            info?.merge_supported === false ? info?.unsupported_reason || '' : ''
        } catch (error) {
          mergeSupported.value = true
          unsupportedReason.value = ''
          tableInfoExtra.value = null
        }

        if (FeatureManager.isEnabled('demoMode')) {
          mergeSupported.value = false
          unsupportedReason.value = '演示模式下仅展示缓存信息，治理操作已禁用'
        }
      }
    } catch (error) {
      console.error('Failed to load table info:', error)
      ElMessage.error('加载表信息失败')
    } finally {
      if (!options.skipLoading) {
        loading.value = false
      }
    }
  }

  return {
    loading,
    tableMetric,
    tableInfoExtra,
    mergeSupported,
    unsupportedReason,
    loadTableInfo
  }
}
