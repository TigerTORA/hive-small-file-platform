import { ref, computed, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { tablesApi } from '@/api/tables'
import { FeatureManager } from '@/utils/feature-flags'
import { getProgressColor } from '@/utils/tableHelpers'

export const usePartitionManagement = (
  clusterId: Ref<number>,
  database: Ref<string>,
  tableName: Ref<string>
) => {
  // 分区统计数据
  const partitionLoading = ref(false)
  const partitionError = ref('')
  const partitionItems = ref<any[]>([])
  const partitionTotal = ref(0)
  const partitionPage = ref(1)
  const partitionPageSize = ref(50)
  const partitionConcurrency = ref(5)

  // 分区选择相关
  const partitionOptions = ref<string[]>([])
  const selectedPartitions = ref<string[]>([])
  const partitionSelectMode = ref<'smart' | 'manual'>('smart')
  const timeRangeMode = ref<'recent' | 'range' | 'pattern'>('recent')

  // 智能选择参数
  const recentDays = ref(7)
  const predictedRecentCount = ref(0)
  const dateRange = ref<[string, string] | null>(null)
  const excludeWeekends = ref(false)
  const predictedRangeCount = ref(0)
  const partitionPattern = ref('')
  const predictedPatternCount = ref(0)

  // 手动选择参数
  const partitionSearchText = ref('')
  const filteredPartitions = ref<string[]>([])
  const paginatedPartitions = ref<string[]>([])
  const currentPartitionPage = ref(1)

  const hasMorePartitions = computed(() => {
    return paginatedPartitions.value.length < filteredPartitions.value.length
  })

  const remainingPartitions = computed(() => {
    return filteredPartitions.value.length - paginatedPartitions.value.length
  })

  const calcPartitionSmallRatio = (row: any): number => {
    const files = Number(row?.file_count || 0)
    const small = Number(row?.small_file_count || 0)
    if (!files) return 0
    return Math.round((small / files) * 100)
  }

  const demoMode = FeatureManager.isEnabled('demoMode')

  const loadPartitionMetrics = async () => {
    partitionLoading.value = true
    partitionError.value = ''
    if (demoMode) {
      partitionItems.value = []
      partitionTotal.value = 0
      partitionLoading.value = false
      partitionError.value = '演示模式未连接 Hive，分区统计已禁用'
      return
    }
    try {
      const { items, total } = await tablesApi.getPartitionMetrics(
        clusterId.value,
        database.value,
        tableName.value,
        partitionPage.value,
        partitionPageSize.value,
        partitionConcurrency.value
      )
      partitionItems.value = items || []
      partitionTotal.value = total || 0
    } catch (error: any) {
      console.error('Failed to load partition metrics:', error)
      partitionError.value = error?.message || '加载分区统计失败'
    } finally {
      partitionLoading.value = false
    }
  }

  const refreshPartitionMetrics = async () => {
    if (demoMode) {
      partitionError.value = '演示模式未连接 Hive，分区统计已禁用'
      return
    }
    await loadPartitionMetrics()
  }

  const handlePartitionSizeChange = async (size: number) => {
    partitionPageSize.value = size
    partitionPage.value = 1
    await loadPartitionMetrics()
  }

  const handlePartitionPageChange = async (page: number) => {
    partitionPage.value = page
    await loadPartitionMetrics()
  }

  // 智能选择方法
  const onPartitionModeChange = (mode: 'smart' | 'manual') => {
    if (mode === 'manual') {
      updateFilteredPartitions()
      updatePaginatedPartitions()
    }
  }

  const onTimeRangeModeChange = () => {
    updatePredictions()
  }

  const onRecentDaysChange = () => {
    updatePredictions()
  }

  const selectRecentPartitions = () => {
    const today = new Date()
    const cutoffDate = new Date(today.getTime() - recentDays.value * 24 * 60 * 60 * 1000)

    const recentPartitions = partitionOptions.value.filter(partition => {
      const match = partition.match(/dt=(\d{4}-\d{2}-\d{2})/)
      if (match) {
        const partitionDate = new Date(match[1])
        return partitionDate >= cutoffDate
      }
      return false
    })

    selectedPartitions.value = recentPartitions
    ElMessage.success(`已选择最近${recentDays.value}天的${recentPartitions.length}个分区`)
  }

  const onDateRangeChange = () => {
    updatePredictions()
  }

  const selectDateRangePartitions = () => {
    if (!dateRange.value || dateRange.value.length !== 2) {
      ElMessage.warning('请选择日期范围')
      return
    }

    const [startDate, endDate] = dateRange.value
    const start = new Date(startDate)
    const end = new Date(endDate)

    const rangePartitions = partitionOptions.value.filter(partition => {
      const match = partition.match(/dt=(\d{4}-\d{2}-\d{2})/)
      if (match) {
        const partitionDate = new Date(match[1])
        const isInRange = partitionDate >= start && partitionDate <= end

        if (excludeWeekends.value && isInRange) {
          const dayOfWeek = partitionDate.getDay()
          return dayOfWeek !== 0 && dayOfWeek !== 6
        }

        return isInRange
      }
      return false
    })

    selectedPartitions.value = rangePartitions
    ElMessage.success(`已选择${startDate}至${endDate}的${rangePartitions.length}个分区`)
  }

  const onPatternChange = () => {
    updatePredictions()
  }

  const selectPatternPartitions = () => {
    if (!partitionPattern.value.trim()) {
      ElMessage.warning('请输入匹配模式')
      return
    }

    const matchedPartitions = matchPartitionsByPattern(partitionPattern.value)
    selectedPartitions.value = matchedPartitions
    ElMessage.success(`模式匹配到${matchedPartitions.length}个分区`)
  }

  const previewPattern = () => {
    if (!partitionPattern.value.trim()) {
      ElMessage.warning('请输入匹配模式')
      return
    }

    const matchedPartitions = matchPartitionsByPattern(partitionPattern.value)
    const previewText = matchedPartitions.slice(0, 10).join(', ') +
      (matchedPartitions.length > 10 ? ` ... (共${matchedPartitions.length}个)` : '')

    ElMessageBox.alert(previewText || '无匹配分区', '模式匹配预览')
  }

  const matchPartitionsByPattern = (pattern: string): string[] => {
    const trimmedPattern = pattern.trim().toLowerCase()

    return partitionOptions.value.filter(partition => {
      const lowerPartition = partition.toLowerCase()

      if (trimmedPattern.includes('*') || trimmedPattern.includes('?')) {
        const regexPattern = trimmedPattern
          .replace(/\*/g, '.*')
          .replace(/\?/g, '.')
        const regex = new RegExp('^' + regexPattern + '$')
        return regex.test(lowerPartition)
      }

      if (trimmedPattern.includes('>=') || trimmedPattern.includes('<=') ||
          trimmedPattern.includes('>') || trimmedPattern.includes('<')) {
        const match = partition.match(/dt=(\d{4}-\d{2}-\d{2})/)
        if (match) {
          const partitionDate = match[1]

          if (trimmedPattern.includes('>=')) {
            const compareDate = trimmedPattern.split('>=')[1].trim().replace(/['"]/g, '')
            return partitionDate >= compareDate
          }
          if (trimmedPattern.includes('<=')) {
            const compareDate = trimmedPattern.split('<=')[1].trim().replace(/['"]/g, '')
            return partitionDate <= compareDate
          }
          if (trimmedPattern.includes('>')) {
            const compareDate = trimmedPattern.split('>')[1].trim().replace(/['"]/g, '')
            return partitionDate > compareDate
          }
          if (trimmedPattern.includes('<')) {
            const compareDate = trimmedPattern.split('<')[1].trim().replace(/['"]/g, '')
            return partitionDate < compareDate
          }
        }
      }

      return lowerPartition.includes(trimmedPattern)
    })
  }

  // 手动选择方法
  const onPartitionSearch = () => {
    updateFilteredPartitions()
    updatePaginatedPartitions()
  }

  const updateFilteredPartitions = () => {
    if (!partitionSearchText.value.trim()) {
      filteredPartitions.value = [...partitionOptions.value]
    } else {
      const searchText = partitionSearchText.value.toLowerCase()
      filteredPartitions.value = partitionOptions.value.filter(partition =>
        partition.toLowerCase().includes(searchText)
      )
    }
  }

  const updatePaginatedPartitions = () => {
    const startIndex = 0
    const endIndex = currentPartitionPage.value * partitionPageSize.value
    paginatedPartitions.value = filteredPartitions.value.slice(startIndex, endIndex)
  }

  const selectAllFiltered = () => {
    const newSelections = filteredPartitions.value.filter(p => !selectedPartitions.value.includes(p))
    selectedPartitions.value.push(...newSelections)
    ElMessage.success(`已选择${newSelections.length}个筛选结果`)
  }

  const loadMorePartitions = () => {
    currentPartitionPage.value++
    updatePaginatedPartitions()
  }

  const clearSelectedPartitions = () => {
    selectedPartitions.value = []
  }

  const showSelectedDetails = () => {
    const details = selectedPartitions.value.slice(0, 50).join(', ') +
      (selectedPartitions.value.length > 50 ? ` ... (共${selectedPartitions.value.length}个)` : '')

    ElMessageBox.alert(details, '已选择的分区详情', {
      confirmButtonText: '确定',
      type: 'info'
    })
  }

  const updatePredictions = () => {
    const today = new Date()
    const cutoffDate = new Date(today.getTime() - recentDays.value * 24 * 60 * 60 * 1000)
    predictedRecentCount.value = partitionOptions.value.filter(partition => {
      const match = partition.match(/dt=(\d{4}-\d{2}-\d{2})/)
      return match && new Date(match[1]) >= cutoffDate
    }).length

    if (dateRange.value && dateRange.value.length === 2) {
      const [startDate, endDate] = dateRange.value
      const start = new Date(startDate)
      const end = new Date(endDate)

      predictedRangeCount.value = partitionOptions.value.filter(partition => {
        const match = partition.match(/dt=(\d{4}-\d{2}-\d{2})/)
        if (match) {
          const partitionDate = new Date(match[1])
          const isInRange = partitionDate >= start && partitionDate <= end

          if (excludeWeekends.value && isInRange) {
            const dayOfWeek = partitionDate.getDay()
            return dayOfWeek !== 0 && dayOfWeek !== 6
          }

          return isInRange
        }
        return false
      }).length
    }

    if (partitionPattern.value.trim()) {
      predictedPatternCount.value = matchPartitionsByPattern(partitionPattern.value).length
    } else {
      predictedPatternCount.value = 0
    }
  }

  const resetPartitionSelection = () => {
    selectedPartitions.value = []
    partitionSelectMode.value = 'smart'
    timeRangeMode.value = 'recent'
    recentDays.value = 7
    dateRange.value = null
    excludeWeekends.value = false
    partitionPattern.value = ''
    partitionSearchText.value = ''
    currentPartitionPage.value = 1
    updatePredictions()
    updateFilteredPartitions()
    updatePaginatedPartitions()
  }

  return {
    // State
    partitionLoading,
    partitionError,
    partitionItems,
    partitionTotal,
    partitionPage,
    partitionPageSize,
    partitionConcurrency,
    partitionOptions,
    selectedPartitions,
    partitionSelectMode,
    timeRangeMode,
    recentDays,
    predictedRecentCount,
    dateRange,
    excludeWeekends,
    predictedRangeCount,
    partitionPattern,
    predictedPatternCount,
    partitionSearchText,
    filteredPartitions,
    paginatedPartitions,
    currentPartitionPage,
    hasMorePartitions,
    remainingPartitions,

    // Methods
    calcPartitionSmallRatio,
    loadPartitionMetrics,
    refreshPartitionMetrics,
    handlePartitionSizeChange,
    handlePartitionPageChange,
    onPartitionModeChange,
    onTimeRangeModeChange,
    onRecentDaysChange,
    selectRecentPartitions,
    onDateRangeChange,
    selectDateRangePartitions,
    onPatternChange,
    selectPatternPartitions,
    previewPattern,
    onPartitionSearch,
    selectAllFiltered,
    loadMorePartitions,
    clearSelectedPartitions,
    showSelectedDetails,
    updatePredictions,
    updateFilteredPartitions,
    updatePaginatedPartitions,
    resetPartitionSelection,
    getProgressColor
  }
}
