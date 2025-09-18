import { ref, onMounted, onUnmounted, watch } from "vue";
import { useMonitoringStore } from "@/stores/monitoring";
import { useDashboardStore } from "@/stores/dashboard";

export function useRealtime() {
  const monitoringStore = useMonitoringStore();
  const dashboardStore = useDashboardStore();

  const isRefreshing = ref(false);
  const nextRefreshIn = ref(0);
  const refreshTimer = ref<NodeJS.Timeout | null>(null);
  const countdownTimer = ref<NodeJS.Timeout | null>(null);

  // 开始自动刷新
  function startAutoRefresh() {
    if (!monitoringStore.isAutoRefreshEnabled) return;

    clearTimers();

    // 设置刷新定时器
    refreshTimer.value = setInterval(async () => {
      await performRefresh();
    }, monitoringStore.settings.refreshInterval * 1000);

    // 开始倒计时
    startCountdown();
  }

  // 停止自动刷新
  function stopAutoRefresh() {
    clearTimers();
    nextRefreshIn.value = 0;
  }

  // 手动刷新
  async function performRefresh() {
    if (isRefreshing.value) return;

    isRefreshing.value = true;

    try {
      await dashboardStore.loadAllData(
        monitoringStore.settings.selectedCluster,
      );
      monitoringStore.lastRefreshTime = new Date();

      // 重新开始倒计时
      startCountdown();
    } catch (error) {
      console.error("刷新数据失败:", error);
    } finally {
      isRefreshing.value = false;
    }
  }

  // 开始倒计时
  function startCountdown() {
    if (!monitoringStore.isAutoRefreshEnabled) return;

    if (countdownTimer.value) {
      clearInterval(countdownTimer.value);
    }

    nextRefreshIn.value = monitoringStore.settings.refreshInterval;

    countdownTimer.value = setInterval(() => {
      nextRefreshIn.value--;
      if (nextRefreshIn.value <= 0) {
        nextRefreshIn.value = monitoringStore.settings.refreshInterval;
      }
    }, 1000);
  }

  // 清理定时器
  function clearTimers() {
    if (refreshTimer.value) {
      clearInterval(refreshTimer.value);
      refreshTimer.value = null;
    }

    if (countdownTimer.value) {
      clearInterval(countdownTimer.value);
      countdownTimer.value = null;
    }
  }

  // 监听自动刷新设置变化
  watch(
    () => monitoringStore.isAutoRefreshEnabled,
    (enabled) => {
      if (enabled) {
        startAutoRefresh();
      } else {
        stopAutoRefresh();
      }
    },
  );

  // 监听刷新间隔变化
  watch(
    () => monitoringStore.settings.refreshInterval,
    () => {
      if (monitoringStore.isAutoRefreshEnabled) {
        startAutoRefresh();
      }
    },
  );

  // 监听选中集群变化
  watch(
    () => monitoringStore.settings.selectedCluster,
    () => {
      // 立即刷新新集群数据
      performRefresh();
    },
  );

  // 生命周期
  onMounted(() => {
    monitoringStore.initialize();

    if (monitoringStore.isAutoRefreshEnabled) {
      startAutoRefresh();
    }
  });

  onUnmounted(() => {
    clearTimers();
    monitoringStore.cleanup();
  });

  return {
    isRefreshing,
    nextRefreshIn,
    performRefresh,
    startAutoRefresh,
    stopAutoRefresh,
  };
}
