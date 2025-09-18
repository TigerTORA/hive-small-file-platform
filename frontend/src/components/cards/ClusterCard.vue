<template>
  <el-card
    class="cluster-card"
    shadow="hover"
  >
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon
            class="header-icon"
            :size="20"
          >
            <Connection />
          </el-icon>
          <span class="header-title">{{ showExtendedStats ? '集群概览' : '集群统计' }}</span>
        </div>
        <div class="header-right">
          <el-tag
            :type="statusType"
            size="small"
          >
            {{ statusText }}
          </el-tag>
        </div>
      </div>
    </template>

    <div class="card-content">
      <div
        class="metrics-grid"
        :class="{ extended: showExtendedStats }"
      >
        <div class="metric-item">
          <div class="metric-value">{{ formatNumber(totalClusters) }}</div>
          <div class="metric-label">总集群数</div>
        </div>

        <div class="metric-item">
          <div class="metric-value active">{{ formatNumber(activeClusters) }}</div>
          <div class="metric-label">活跃集群</div>
        </div>

        <!-- 扩展统计信息 -->
        <template v-if="showExtendedStats">
          <div class="metric-item">
            <div class="metric-value table">{{ formatNumber(totalTables) }}</div>
            <div class="metric-label">总表数</div>
          </div>

          <div class="metric-item">
            <div class="metric-value file">{{ formatNumber(totalFiles) }}</div>
            <div class="metric-label">总文件数</div>
          </div>
        </template>
      </div>

      <div class="cluster-progress">
        <div class="progress-info">
          <span class="progress-label">集群活跃率</span>
          <span class="progress-percent">{{ activeRate }}%</span>
        </div>
        <el-progress
          :percentage="activeRate"
          :color="progressColor"
          :show-text="false"
          stroke-width="8"
        />
      </div>

      <div
        class="cluster-selector"
        v-if="showSelector"
      >
        <el-select
          :model-value="selectedClusterId"
          @update:model-value="handleClusterChange"
          placeholder="选择集群"
          style="width: 100%"
          size="small"
        >
          <el-option
            v-for="cluster in clusters"
            :key="cluster.id"
            :label="`${cluster.name} (${cluster.status})`"
            :value="cluster.id"
          />
        </el-select>
      </div>
    </div>

    <div
      class="card-footer"
      v-if="showFooter"
    >
      <div class="footer-stats">
        <span class="stat-item">
          <el-icon :size="14"><Clock /></el-icon>
          最后更新: {{ lastUpdateTime }}
        </span>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { Connection, Clock } from '@element-plus/icons-vue'
  import { useDashboardStore } from '@/stores/dashboard'
  import { useMonitoringStore } from '@/stores/monitoring'

  interface Props {
    showSelector?: boolean
    showFooter?: boolean
    showExtendedStats?: boolean
  }

  const props = withDefaults(defineProps<Props>(), {
    showSelector: true,
    showFooter: true,
    showExtendedStats: false
  })

  const emit = defineEmits<{
    clusterChange: [clusterId: number]
  }>()

  const dashboardStore = useDashboardStore()
  const monitoringStore = useMonitoringStore()

  // 计算属性
  const totalClusters = computed(() => dashboardStore.summary.total_clusters)
  const activeClusters = computed(() => dashboardStore.summary.active_clusters)
  const totalTables = computed(() => dashboardStore.summary.total_tables || 0)
  const totalFiles = computed(() => dashboardStore.summary.total_files || 0)

  const activeRate = computed(() => {
    if (totalClusters.value === 0) return 0
    return Math.round((activeClusters.value / totalClusters.value) * 100)
  })

  const statusType = computed(() => {
    const rate = activeRate.value
    if (rate >= 80) return 'success'
    if (rate >= 60) return 'warning'
    return 'danger'
  })

  const statusText = computed(() => {
    const rate = activeRate.value
    if (rate >= 80) return '良好'
    if (rate >= 60) return '一般'
    return '异常'
  })

  const progressColor = computed(() => {
    const rate = activeRate.value
    if (rate >= 80) return '#67C23A'
    if (rate >= 60) return '#E6A23C'
    return '#F56C6C'
  })

  const clusters = computed(() => dashboardStore.clusterStats)
  const selectedClusterId = computed(() => monitoringStore.settings.selectedCluster)

  const lastUpdateTime = computed(() => {
    if (!monitoringStore.lastRefreshTime) return '--'
    return monitoringStore.formatDate(monitoringStore.lastRefreshTime)
  })

  // 方法
  function formatNumber(num: number): string {
    return monitoringStore.formatNumber(num)
  }

  function handleClusterChange(clusterId: number) {
    monitoringStore.setSelectedCluster(clusterId)
    emit('clusterChange', clusterId)
  }
</script>

<style scoped>
  .cluster-card {
    border-radius: 12px;
    transition: all 0.3s ease;
  }

  .cluster-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .header-icon {
    color: #409eff;
  }

  .header-title {
    font-weight: 600;
    color: #333;
    font-size: 16px;
  }

  .card-content {
    padding-top: 8px;
  }

  .metrics-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 20px;
  }

  .metrics-grid.extended {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 12px;
  }

  .metric-item {
    text-align: center;
    padding: 16px;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-radius: 8px;
  }

  .metric-value {
    font-size: 28px;
    font-weight: bold;
    color: #409eff;
    margin-bottom: 4px;
  }

  .metric-value.active {
    color: #67c23a;
  }

  .metric-value.table {
    color: #e6a23c;
  }

  .metric-value.file {
    color: #909399;
  }

  .metric-label {
    font-size: 12px;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .cluster-progress {
    margin-bottom: 20px;
  }

  .progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .progress-label {
    font-size: 14px;
    color: #666;
  }

  .progress-percent {
    font-size: 14px;
    font-weight: bold;
    color: #333;
  }

  .cluster-selector {
    margin-bottom: 12px;
  }

  .card-footer {
    padding-top: 12px;
    border-top: 1px solid #f0f0f0;
    margin-top: 8px;
  }

  .footer-stats {
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .stat-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: #999;
  }

  @media (max-width: 768px) {
    .metrics-grid {
      grid-template-columns: 1fr;
      gap: 12px;
    }

    .metric-item {
      padding: 12px;
    }

    .metric-value {
      font-size: 24px;
    }
  }
</style>
