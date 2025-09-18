<template>
  <div class="cluster-selector">
    <div class="selector-header">
      <h2 class="selector-title">
        <el-icon><Connection /></el-icon>
        选择集群
      </h2>
      <p class="selector-subtitle">
        请选择要监控的 Hive 集群，查看详细的数据生命周期管理信息
      </p>
    </div>

    <div v-loading="loading" class="cluster-grid">
      <div v-if="clusters.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无可用集群">
          <el-button type="primary" @click="$router.push('/clusters')">
            去添加集群
          </el-button>
        </el-empty>
      </div>

      <div
        v-for="cluster in clusters"
        :key="cluster.id"
        class="cluster-option"
        :class="{
          'cluster-selected': selectedClusterId === cluster.id,
          'cluster-disabled': cluster.status !== 'active',
        }"
        @click="selectCluster(cluster)"
      >
        <div class="cluster-info">
          <div class="cluster-name">
            {{ cluster.name }}
          </div>
          <div class="cluster-meta">
            <span class="cluster-type">{{
              getClusterTypeText(cluster.cluster_type)
            }}</span>
            <el-tag
              :type="cluster.status === 'active' ? 'success' : 'danger'"
              size="small"
            >
              {{ cluster.status === "active" ? "正常" : "异常" }}
            </el-tag>
          </div>
          <div class="cluster-details">
            <div class="detail-item">
              <span class="detail-label">Hive:</span>
              <span class="detail-value"
                >{{ cluster.hive_host }}:{{ cluster.hive_port }}</span
              >
            </div>
            <div class="detail-item">
              <span class="detail-label">数据库:</span>
              <span class="detail-value"
                >{{ clusterStats[cluster.id]?.databases || 0 }} 个</span
              >
            </div>
          </div>
        </div>

        <div class="cluster-stats" v-if="clusterStats[cluster.id]">
          <div class="stat-item">
            <div class="stat-value">
              {{ formatNumber(clusterStats[cluster.id].tables) }}
            </div>
            <div class="stat-label">表数量</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">
              {{ formatNumber(clusterStats[cluster.id].small_files) }}
            </div>
            <div class="stat-label">小文件数</div>
          </div>
        </div>

        <div
          class="selection-indicator"
          v-if="selectedClusterId === cluster.id"
        >
          <el-icon><CircleCheckFilled /></el-icon>
        </div>
      </div>
    </div>

    <div class="selector-actions" v-if="selectedClusterId">
      <el-button size="large" @click="$emit('cancel')">取消</el-button>
      <el-button
        type="primary"
        size="large"
        @click="confirmSelection"
        :loading="confirming"
      >
        进入监控中心
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { Connection, CircleCheckFilled } from "@element-plus/icons-vue";
import { clustersApi } from "@/api/clusters";
import { useMonitoringStore } from "@/stores/monitoring";

interface Cluster {
  id: number;
  name: string;
  cluster_type: string;
  status: string;
  hive_host: string;
  hive_port: number;
}

interface ClusterStats {
  databases: number;
  tables: number;
  small_files: number;
}

const emit = defineEmits<{
  confirm: [clusterId: number];
  cancel: [];
}>();

const monitoringStore = useMonitoringStore();

const loading = ref(false);
const confirming = ref(false);
const clusters = ref<Cluster[]>([]);
const clusterStats = ref<Record<number, ClusterStats>>({});
const selectedClusterId = ref<number | null>(null);

const loadClusters = async () => {
  loading.value = true;
  try {
    clusters.value = await clustersApi.list();

    if (clusters.value.length === 0) {
      return; // 如果没有集群，不需要加载统计信息
    }

    await loadClusterStats();

    // 如果只有一个可用集群，自动选中
    const activeClusters = clusters.value.filter((c) => c.status === "active");
    if (activeClusters.length === 1) {
      selectedClusterId.value = activeClusters[0].id;
    }
  } catch (error) {
    console.error("Failed to load clusters:", error);
    // 显示用户友好的错误提示
    import("element-plus").then(({ ElMessage }) => {
      ElMessage.error("加载集群列表失败，请检查网络连接");
    });
  } finally {
    loading.value = false;
  }
};

const loadClusterStats = async () => {
  const stats: Record<number, ClusterStats> = {};

  for (const cluster of clusters.value) {
    if (cluster.status === "active") {
      try {
        const clusterStatsData = await clustersApi.getStats(cluster.id);
        stats[cluster.id] = {
          databases: clusterStatsData.total_databases,
          tables: clusterStatsData.total_tables,
          small_files: clusterStatsData.total_small_files,
        };
      } catch (error) {
        console.error(`Failed to load stats for cluster ${cluster.id}:`, error);
        stats[cluster.id] = {
          databases: 0,
          tables: 0,
          small_files: 0,
        };
      }
    }
  }

  clusterStats.value = stats;
};

const selectCluster = (cluster: Cluster) => {
  if (cluster.status !== "active") return;
  selectedClusterId.value = cluster.id;
};

const confirmSelection = async () => {
  if (!selectedClusterId.value) return;

  confirming.value = true;
  try {
    // 保存选择的集群到监控设置中
    monitoringStore.setSelectedCluster(selectedClusterId.value);

    // 发出确认事件
    emit("confirm", selectedClusterId.value);
  } catch (error) {
    console.error("Failed to confirm cluster selection:", error);
  } finally {
    confirming.value = false;
  }
};

const getClusterTypeText = (type: string): string => {
  const typeMap: Record<string, string> = {
    cdp: "CDP",
    cdh: "CDH",
    hdp: "HDP",
    apache: "Apache Hadoop",
  };
  return typeMap[type] || type;
};

const formatNumber = (num: number): string => {
  return monitoringStore.formatNumber(num);
};

onMounted(() => {
  loadClusters();
});
</script>

<style scoped>
.cluster-selector {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-8);
}

/* 头部 */
.selector-header {
  text-align: center;
  margin-bottom: var(--space-10);
}

.selector-title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--gray-900);
  margin-bottom: var(--space-4);
}

.selector-title .el-icon {
  color: var(--primary-500);
}

.selector-subtitle {
  font-size: var(--text-lg);
  color: var(--gray-600);
  max-width: 600px;
  margin: 0 auto;
  line-height: 1.6;
}

/* 集群网格 */
.cluster-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: var(--space-6);
  margin-bottom: var(--space-10);
}

.cluster-option {
  background: var(--bg-primary);
  border: 2px solid var(--gray-200);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  cursor: pointer;
  transition: all var(--transition-normal);
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
}

.cluster-option:hover:not(.cluster-disabled) {
  border-color: var(--primary-300);
  transform: translateY(-2px);
  box-shadow: var(--elevation-2);
}

.cluster-option.cluster-selected {
  border-color: var(--primary-500);
  background: var(--primary-50);
  box-shadow: var(--elevation-3);
}

.cluster-option.cluster-disabled {
  background: var(--gray-50);
  border-color: var(--gray-200);
  cursor: not-allowed;
  opacity: 0.6;
}

/* 集群信息 */
.cluster-info {
  flex: 1;
}

.cluster-name {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
  margin-bottom: var(--space-3);
}

.cluster-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.cluster-type {
  font-size: var(--text-sm);
  color: var(--gray-600);
  background: var(--gray-100);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-md);
}

.cluster-details {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.detail-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.detail-label {
  color: var(--gray-600);
  min-width: 50px;
}

.detail-value {
  color: var(--gray-900);
  font-family: var(--font-mono);
}

/* 集群统计 */
.cluster-stats {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 80px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--primary-600);
  line-height: 1.2;
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--gray-600);
  margin-top: var(--space-1);
}

/* 选择指示器 */
.selection-indicator {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  color: var(--primary-500);
  font-size: var(--text-xl);
}

/* 操作按钮 */
.selector-actions {
  display: flex;
  justify-content: center;
  gap: var(--space-4);
  padding-top: var(--space-8);
  border-top: 1px solid var(--gray-200);
}

/* 空状态 */
.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: var(--space-16);
}

/* 响应式适配 */
@media (max-width: 768px) {
  .cluster-selector {
    padding: var(--space-4);
  }

  .cluster-grid {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }

  .cluster-option {
    padding: var(--space-4);
  }

  .selector-actions {
    flex-direction: column;
  }
}
</style>
