import { ref, computed, watch, onBeforeUnmount } from 'vue'
import type { Ref } from 'vue'
import type { MergeTask } from '@/api/tasks'

/**
 * 任务轮询和进度监控
 */
export function useTaskPolling(tasks: Ref<MergeTask[]>, loadTasks: () => Promise<void>) {
  const pollingInterval = ref<NodeJS.Timeout | null>(null)

  // 检查是否有运行中的任务
  const hasRunningTasks = computed(() => {
    return tasks.value.some(task => task.status === 'running')
  })

  // 启动任务状态轮询
  const startPolling = () => {
    if (pollingInterval.value) return

    pollingInterval.value = setInterval(() => {
      if (hasRunningTasks.value) {
        loadTasks()
      } else {
        stopPolling()
      }
    }, 3000)
  }

  // 停止任务状态轮询
  const stopPolling = () => {
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
    }
  }

  // 监听任务状态变化，自动启动/停止轮询
  watch(
    () => hasRunningTasks.value,
    hasRunning => {
      if (hasRunning) {
        startPolling()
      } else {
        stopPolling()
      }
    }
  )

  // 组件卸载时清理轮询
  onBeforeUnmount(() => {
    stopPolling()
  })

  return {
    hasRunningTasks,
    startPolling,
    stopPolling
  }
}

/**
 * 扫描任务自动刷新
 */
export function useScanAutoRefresh(
  scanAutoRefresh: Ref<number>,
  loadScanTasks: () => Promise<void>
) {
  let scanRefreshTimer: NodeJS.Timeout | null = null

  const setupScanAutoRefresh = () => {
    if (scanRefreshTimer) {
      clearInterval(scanRefreshTimer)
      scanRefreshTimer = null
    }
    if (scanAutoRefresh.value > 0) {
      scanRefreshTimer = setInterval(() => {
        loadScanTasks()
      }, scanAutoRefresh.value * 1000)
    }
  }

  watch(scanAutoRefresh, setupScanAutoRefresh)

  onBeforeUnmount(() => {
    if (scanRefreshTimer) {
      clearInterval(scanRefreshTimer)
      scanRefreshTimer = null
    }
  })

  return {
    setupScanAutoRefresh
  }
}
