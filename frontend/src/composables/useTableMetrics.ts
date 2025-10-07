import { computed, type Ref } from 'vue'
import dayjs from 'dayjs'
import type { TableMetric } from '@/api/tables'
import { formatFileSize } from '@/utils/formatFileSize'
import { formatNumber, formatTime } from '@/utils/tableHelpers'

export interface RecommendationItem {
  id: string
  icon: string
  severity: 'danger' | 'warning' | 'info' | 'success'
  title: string
  summary: string
  tips?: string[]
  copyText?: string
}

export const useTableMetrics = (
  tableMetric: Ref<TableMetric | null>,
  tableInfoExtra: Ref<any | null>
) => {
  const tableInfoSource = computed(() => ({
    ...(tableMetric.value || {}),
    ...(tableInfoExtra.value || {})
  }))

  const storageFormatTag = computed(() => {
    const format = (tableInfoSource.value.storage_format || '').toString().toUpperCase()
    return format || ''
  })

  const compressionLabel = computed(() => {
    const raw = (tableInfoSource.value.current_compression || '').toString().toUpperCase()
    if (!raw || raw === 'DEFAULT') return '默认'
    return raw
  })

  const tableTypeTag = computed(() => {
    const raw = (tableInfoSource.value.table_type || '').toString().toUpperCase()
    switch (raw) {
      case 'MANAGED_TABLE':
        return { label: '托管表', type: 'success' as const }
      case 'EXTERNAL_TABLE':
        return { label: '外部表', type: 'warning' as const }
      case 'VIEW':
        return { label: '视图', type: 'info' as const }
      default:
        return { label: raw || '未知', type: 'info' as const }
    }
  })

  const tableLocationRaw = computed(() => (tableInfoSource.value.table_path || '').toString())
  const tableLocationDisplay = computed(() => tableLocationRaw.value || '--')

  const partitionColumnsLabel = computed(() => {
    const raw = tableInfoSource.value.partition_columns
    if (!raw) return '--'
    try {
      const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
      if (Array.isArray(parsed)) {
        return parsed.join(', ')
      }
    } catch (error) {
      return String(raw)
    }
    return String(raw)
  })

  const archiveStatusLabel = computed(() => {
    const label = (tableInfoSource.value.archive_status || '').toString()
    if (!label) return '未归档'
    return label.toUpperCase()
  })

  const isArchived = computed(() => (tableMetric.value?.archive_status || '').toLowerCase() === 'archived')

  const lastAccessLabel = computed(() => {
    const access = tableInfoSource.value.last_access_time
    if (!access) return '--'
    return `${formatTime(access)}（${dayjs(access).fromNow()}）`
  })

  const coldDataLabel = computed(() => {
    if (!tableMetric.value) return '--'
    if (tableMetric.value.is_cold_data) {
      const days = tableMetric.value.days_since_last_access ?? 0
      return `冷数据（${days} 天未访问）`
    }
    return '活跃'
  })

  const smallFileRatio = computed(() => {
    if (!tableMetric.value || !tableMetric.value.total_files) return 0
    return Math.round((tableMetric.value.small_files / tableMetric.value.total_files) * 100)
  })

  const summaryMeta = computed(() => {
    const scanTime = tableMetric.value?.scan_time
    if (!scanTime) {
      return { lastScanText: '--', lastScanFromNow: '' }
    }
    const formatted = formatTime(scanTime)
    const relative = dayjs(scanTime).isValid() ? dayjs(scanTime).fromNow() : ''
    return { lastScanText: formatted, lastScanFromNow: relative }
  })

  const summaryStats = computed(() => {
    if (!tableMetric.value) return []
    const ratio = smallFileRatio.value
    const files = tableMetric.value.total_files
    const smallFiles = tableMetric.value.small_files

    const severity = ratio >= 80 ? 'danger' : ratio >= 50 ? 'warning' : ratio > 0 ? 'primary' : 'success'

    const totalSize = typeof tableMetric.value.total_size === 'number' ? tableMetric.value.total_size : null
    const avgSize = typeof tableMetric.value.avg_file_size === 'number' ? tableMetric.value.avg_file_size : null
    const totalSizeLabel = totalSize !== null ? formatFileSize(totalSize) : '--'
    const avgSizeLabel = avgSize !== null ? formatFileSize(avgSize) : '--'

    const stats = [
      {
        label: '小文件占比',
        value: `${ratio}%`,
        icon: 'PieChart',
        color: severity,
        description: files ? `小文件 ${formatNumber(smallFiles)} / 总数 ${formatNumber(files)}` : '暂无文件'
      },
      {
        label: '小文件数',
        value: formatNumber(smallFiles),
        icon: 'DocumentDelete',
        color: severity,
        description: `总文件数 ${formatNumber(files)}`
      },
      {
        label: '表数据量',
        value: totalSizeLabel,
        icon: 'DataAnalysis',
        color: 'primary',
        description: `平均大小 ${avgSizeLabel}`
      }
    ]

    if (tableMetric.value.is_partitioned) {
      const partitionCount = tableMetric.value.partition_count || 0
      const avgPerPartition = partitionCount
        ? Math.max(1, Math.round(tableMetric.value.total_files / partitionCount))
        : 0
      stats.push({
        label: '分区数量',
        value: formatNumber(partitionCount),
        icon: 'Grid',
        color: 'info',
        description: partitionCount ? `平均 ${formatNumber(avgPerPartition)} 文件/分区` : '暂无分区数据'
      })
    }

    return stats
  })

  const getSmallFileImpact = (): string => {
    const ratio = smallFileRatio.value
    if (ratio >= 80) return '严重影响查询性能，强烈建议立即进行文件合并优化'
    if (ratio >= 50) return '显著影响查询效率，建议尽快进行文件合并优化'
    if (ratio >= 20) return '轻微影响查询性能，建议安排文件合并任务'
    return '小文件数量较少，但仍建议定期进行文件整理'
  }

  const getSmallFileSuggestions = (): string[] => {
    if (!tableMetric.value) return []
    const suggestions: string[] = []
    const ratio = smallFileRatio.value

    if (ratio >= 80) {
      suggestions.push('立即执行安全合并策略，可显著降低查询开销')
      suggestions.push('检查写入链路，避免产生更多小文件')
    } else if (ratio >= 50) {
      suggestions.push('使用安全合并策略进行文件合并')
      suggestions.push('建议在业务低峰期执行合并任务')
    } else {
      suggestions.push('可择机进行文件合并优化')
      suggestions.push('监控后续写入，防止小文件累积')
    }

    if (tableMetric.value.is_partitioned) {
      suggestions.push('分区表可按分区逐步合并，降低对业务的影响')
    }

    if ((tableMetric.value.storage_format || '').toUpperCase() === 'TEXT') {
      suggestions.push('考虑转换为 ORC / Parquet 等列式格式以提升性能')
    }

    return suggestions
  }

  const getStorageFormatAdvice = (): string | null => {
    if (!tableMetric.value) return null

    const format = (tableMetric.value.storage_format || '').toUpperCase()
    const totalSize = tableMetric.value.total_size

    if (format === 'TEXT') {
      if (totalSize > 100 * 1024 * 1024) {
        return '当前使用 TEXT 格式，建议转换为 ORC 或 Parquet，预计可减少存储开销并显著提升查询性能'
      }
      return 'TEXT 格式不支持列式优化，仍建议评估升级为 ORC 或 Parquet'
    }

    if (format === 'SEQUENCE' || format === 'AVRO') {
      return `${format} 格式功能完整但性能逊于列式存储，建议评估转换到 ORC/Parquet 的可行性`
    }

    if (format === 'ORC' || format === 'PARQUET') {
      return null
    }

    return `建议评估当前 ${format || '未知'} 格式是否最佳，可对比 ORC/Parquet 的压缩与查询表现`
  }

  const getPartitionAdvice = (): string | null => {
    if (!tableMetric.value) return null

    const { is_partitioned, partition_count, total_files, total_size } = tableMetric.value

    if (!is_partitioned) {
      if (total_size > 1024 * 1024 * 1024) {
        return '大表建议引入分区策略（按日期/业务字段），可显著提升查询性能'
      }
      return null
    }

    if (partition_count > 10000) {
      return `分区数量过多（${partition_count} 个），可能造成元数据压力，建议合并小分区或调整策略`
    }

    if (partition_count > 0 && total_files / partition_count < 5) {
      return '平均每个分区文件数过少，建议合并小分区或调整写入批次'
    }

    return null
  }

  const recommendationList = computed<RecommendationItem[]>(() => {
    if (!tableMetric.value) return []

    const items: RecommendationItem[] = []
    const ratio = smallFileRatio.value

    if (tableMetric.value.small_files > 0) {
      const severity = ratio >= 80 ? 'danger' : ratio >= 50 ? 'warning' : 'info'
      const tips = getSmallFileSuggestions()
      const summary = getSmallFileImpact()
      const title = `小文件问题：${formatNumber(tableMetric.value.small_files)} 个（${ratio}%）`
      items.push({
        id: 'small-files',
        icon: severity === 'danger' ? 'WarningFilled' : severity === 'warning' ? 'Warning' : 'InfoFilled',
        severity,
        title,
        summary,
        tips,
        copyText: [title, summary, ...tips].join('\n')
      })
    }

    const storageAdvice = getStorageFormatAdvice()
    if (storageAdvice) {
      items.push({
        id: 'storage',
        icon: 'SetUp',
        severity: 'info',
        title: '存储格式优化',
        summary: storageAdvice,
        copyText: storageAdvice
      })
    }

    const partitionAdvice = getPartitionAdvice()
    if (partitionAdvice) {
      items.push({
        id: 'partition',
        icon: 'Grid',
        severity: 'info',
        title: '分区策略优化',
        summary: partitionAdvice,
        copyText: partitionAdvice
      })
    }

    return items
  })

  const isTableHealthy = computed(() => !!tableMetric.value && tableMetric.value.small_files === 0)

  return {
    tableInfoSource,
    storageFormatTag,
    compressionLabel,
    tableTypeTag,
    tableLocationRaw,
    tableLocationDisplay,
    partitionColumnsLabel,
    archiveStatusLabel,
    isArchived,
    lastAccessLabel,
    coldDataLabel,
    smallFileRatio,
    summaryMeta,
    summaryStats,
    recommendationList,
    isTableHealthy
  }
}
