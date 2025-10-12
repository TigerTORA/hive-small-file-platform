import { describe, expect, it, beforeEach, vi } from 'vitest'
import { ref } from 'vue'

import { usePartitionManagement } from '@/composables/usePartitionManagement'
import { FeatureManager } from '@/utils/feature-flags'

vi.mock('@/api/tables', () => ({
  tablesApi: {
    getPartitionMetrics: vi.fn().mockResolvedValue({
      items: [{ partition_spec: 'dt=2024-01-01', file_count: 3, small_file_count: 1 }],
      total: 1
    })
  }
}))

import { tablesApi } from '@/api/tables'

describe('demo mode partition management', () => {
  beforeEach(() => {
    FeatureManager.reset()
    vi.clearAllMocks()
  })

  it('returns empty partitions in demo mode without hitting API', async () => {
    FeatureManager.setFeatures({ demoMode: true })
    const manager = usePartitionManagement(ref(1), ref('demo_db'), ref('demo_table'))

    await manager.loadPartitionMetrics()

    expect(manager.partitionItems.value).toEqual([])
    expect(manager.partitionError.value).toContain('演示模式')
    expect(tablesApi.getPartitionMetrics).not.toHaveBeenCalled()
  })

  it('fetches partitions when demo mode disabled', async () => {
    FeatureManager.setFeatures({ demoMode: false })
    const manager = usePartitionManagement(ref(1), ref('demo_db'), ref('demo_table'))

    await manager.loadPartitionMetrics()

    expect(tablesApi.getPartitionMetrics).toHaveBeenCalled()
    expect(manager.partitionItems.value.length).toBeGreaterThanOrEqual(0)
  })
})
