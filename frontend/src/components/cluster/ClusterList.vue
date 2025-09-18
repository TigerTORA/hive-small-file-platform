<template>
  <div class="cluster-list">
    <!-- 集群选择提示条 -->
    <div v-if="redirectUrl" class="cluster-selection-notice">
      <div class="notice-content">
        <el-icon class="notice-icon"><Monitor /></el-icon>
        <div class="notice-text">
          <h4>请选择要使用的集群</h4>
          <p>
            您需要先选择一个集群才能访问监控功能。点击任意集群卡片即可选择并继续。
          </p>
        </div>
      </div>
    </div>

    <!-- 集群卡片列表 -->
    <div v-loading="loading" class="clusters-grid">
      <div v-if="filteredClusters.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无集群数据">
          <el-button type="primary" @click="$emit('create-cluster')">
            添加第一个集群
          </el-button>
        </el-empty>
      </div>

      <div
        v-for="cluster in filteredClusters"
        :key="cluster.id"
        class="cloudera-metric-card cluster-card hover-lift"
        @click="$emit('enter-cluster', cluster.id)"
        :class="{ 'cluster-online': cluster.status === 'active' }"
      >
        <div class="cluster-header">
          <div class="cluster-title-section">
            <div class="cluster-name-row">
              <h3 class="cluster-name">{{ cluster.name }}</h3>
              <ConnectionStatusIndicator
                :hiveserver-status="
                  getConnectionStatus(cluster.id, 'hiveserver')
                "
                :hdfs-status="getConnectionStatus(cluster.id, 'hdfs')"
                :metastore-status="getConnectionStatus(cluster.id, 'metastore')"
                :loading="isLoadingConnectionStatus(cluster.id)"
                @test-connection="
                  (service) =>
                    $emit('test-specific-connection', cluster.id, service)
                "
              />
            </div>
            <p class="cluster-description">
              {{ cluster.description || "Cloudera Data Platform 集群" }}
            </p>
          </div>
          <div class="cluster-actions" @click.stop>
            <el-tooltip content="进入集群详情" placement="top">
              <el-button
                size="small"
                circle
                @click="$emit('enter-cluster', cluster.id)"
                class="cloudera-btn primary"
              >
                <el-icon><Right /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </div>

        <div class="cluster-content">
          <div class="cluster-info-compact">
            <div class="cluster-details">
              <div class="detail-item">
                <el-icon><Monitor /></el-icon>
                <span>{{ cluster.hive_host }}:{{ cluster.hive_port }}</span>
              </div>
            </div>
          </div>

          <div class="cluster-stats-compact">
            <div class="stats-row">
              <div class="stat-item">
                <span class="stat-value">{{
                  getClusterStat(cluster.id, "databases")
                }}</span>
                <span class="stat-label">数据库</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <span class="stat-value">{{
                  getClusterStat(cluster.id, "tables")
                }}</span>
                <span class="stat-label">表数量</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <span class="stat-value">{{
                  getClusterStat(cluster.id, "small_files")
                }}</span>
                <span class="stat-label">小文件</span>
              </div>
            </div>
          </div>

          <div class="cluster-operations" @click.stop>
            <el-button
              size="small"
              @click="$emit('test-connection', cluster, 'enhanced')"
              class="cloudera-btn secondary"
            >
              <el-icon><Connection /></el-icon>
              连接测试
            </el-button>
            <el-button
              size="small"
              @click="$emit('edit-cluster', cluster)"
              class="cloudera-btn secondary"
            >
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-dropdown
              @command="(command) => $emit('cluster-action', command, cluster)"
              trigger="click"
            >
              <el-button size="small" class="cloudera-btn secondary">
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="delete" class="danger-item">
                    <el-icon><Delete /></el-icon>
                    删除集群
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import {
  Monitor,
  Right,
  Connection,
  Edit,
  Delete,
  MoreFilled,
} from "@element-plus/icons-vue";
import ConnectionStatusIndicator from "@/components/ConnectionStatusIndicator.vue";
import type { Cluster } from "@/api/clusters";

interface Props {
  clusters: Cluster[];
  loading: boolean;
  clusterStats: Record<number, any>;
  connectionStatus: Record<number, any>;
  searchText: string;
  statusFilter: string;
  redirectUrl?: string;
}

interface Emits {
  (e: "enter-cluster", clusterId: number): void;
  (e: "create-cluster"): void;
  (e: "test-connection", cluster: Cluster, mode: string): void;
  (e: "edit-cluster", cluster: Cluster): void;
  (e: "cluster-action", command: string, cluster: Cluster): void;
  (e: "test-specific-connection", clusterId: number, service: string): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const filteredClusters = computed(() => {
  let result = props.clusters;

  if (props.searchText) {
    const search = props.searchText.toLowerCase();
    result = result.filter(
      (cluster) =>
        cluster.name.toLowerCase().includes(search) ||
        cluster.hive_host.toLowerCase().includes(search) ||
        (cluster.description &&
          cluster.description.toLowerCase().includes(search)),
    );
  }

  if (props.statusFilter) {
    result = result.filter((cluster) => cluster.status === props.statusFilter);
  }

  return result;
});

const getClusterStat = (clusterId: number, type: string) => {
  return props.clusterStats[clusterId]?.[type] || 0;
};

const getConnectionStatus = (clusterId: number, service: string) => {
  const status = props.connectionStatus[clusterId];
  if (!status) return { status: "unknown" };

  switch (service) {
    case "hiveserver":
      return status.hiveserver || { status: "unknown" };
    case "hdfs":
      return status.hdfs || { status: "unknown" };
    case "metastore":
      return status.metastore || { status: "unknown" };
    default:
      return { status: "unknown" };
  }
};

const isLoadingConnectionStatus = (clusterId: number) => {
  return props.connectionStatus[clusterId]?.loading || false;
};
</script>

<style scoped>
.cluster-list {
  width: 100%;
}

.cluster-selection-notice {
  margin-bottom: var(--space-6);
  padding: var(--space-6);
  background: linear-gradient(135deg, var(--primary-50), var(--primary-100));
  border-radius: var(--radius-xl);
  border: 1px solid var(--primary-200);
}

.notice-content {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.notice-icon {
  font-size: var(--text-2xl);
  color: var(--primary-600);
}

.notice-text h4 {
  margin: 0 0 var(--space-1) 0;
  color: var(--primary-800);
  font-weight: var(--font-semibold);
}

.notice-text p {
  margin: 0;
  color: var(--primary-700);
  font-size: var(--text-sm);
}

.clusters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: var(--space-6);
}

.cluster-card {
  cursor: pointer;
  padding: var(--space-6);
  min-height: 240px;
  display: flex;
  flex-direction: column;
}

.cluster-online::before {
  background: linear-gradient(90deg, var(--success-500), var(--success-300));
}

.cluster-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--gray-200);
}

.cluster-title-section {
  flex: 1;
}

.cluster-name-row {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  margin-bottom: var(--space-2) !important;
}

.cluster-name {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
  flex: 1;
  margin-right: var(--space-3);
}

.cluster-title-section .cluster-description {
  color: var(--gray-600);
  margin: 0;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
}

.cluster-actions {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.cluster-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.cluster-info-compact {
  margin-bottom: var(--space-3);
}

.cluster-info-compact .cluster-details {
  display: flex;
  gap: var(--space-4);
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
  color: var(--gray-600);
}

.detail-item .el-icon {
  color: var(--primary-500);
}

.cluster-stats-compact {
  margin-bottom: var(--space-4);
}

.stats-row {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  padding: var(--space-3) var(--space-4) !important;
  background: var(--gray-50) !important;
  border-radius: var(--radius-lg) !important;
  border: 1px solid var(--gray-200) !important;
}

.stats-row .stat-item {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  text-align: center !important;
  flex: 1 !important;
}

.stat-divider {
  width: 1px;
  height: 24px;
  background: var(--gray-300);
  margin: 0 var(--space-2);
}

.stats-row .stat-value {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--primary-600);
  margin-bottom: 2px;
}

.stats-row .stat-label {
  font-size: var(--text-xs);
  color: var(--gray-600);
  font-weight: var(--font-medium);
}

.cluster-operations {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  margin-top: auto;
  padding-top: var(--space-4);
  border-top: 1px solid var(--gray-200);
}

.danger-item {
  color: var(--danger-500) !important;
}

.danger-item .el-icon {
  color: var(--danger-500) !important;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: var(--space-16) var(--space-6);
}

@media (max-width: 1200px) {
  .clusters-grid {
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: var(--space-4);
  }
}

@media (max-width: 768px) {
  .clusters-grid {
    grid-template-columns: 1fr;
  }

  .cluster-operations {
    justify-content: center;
  }
}
</style>
