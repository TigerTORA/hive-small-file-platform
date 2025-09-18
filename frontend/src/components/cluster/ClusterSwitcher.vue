<template>
  <div class="cluster-switcher">
    <el-dropdown
      @command="switchCluster"
      trigger="click"
      placement="bottom-start"
    >
      <div
        class="current-cluster"
        :class="{ 'has-error': currentCluster?.status !== 'active' }"
      >
        <div class="cluster-icon">
          <el-icon><Connection /></el-icon>
        </div>
        <div class="cluster-info">
          <div class="cluster-name">
            {{ currentCluster?.name || "未选择集群" }}
          </div>
          <div class="cluster-status">
            <el-tag
              :type="currentCluster?.status === 'active' ? 'success' : 'danger'"
              size="small"
            >
              {{ getStatusText(currentCluster?.status) }}
            </el-tag>
            <span class="cluster-type">{{
              getClusterTypeText(currentCluster?.cluster_type)
            }}</span>
          </div>
        </div>
        <div class="dropdown-arrow">
          <el-icon><ArrowDown /></el-icon>
        </div>
      </div>

      <template #dropdown>
        <el-dropdown-menu>
          <div class="cluster-dropdown">
            <div class="dropdown-header">
              <span class="dropdown-title">选择集群</span>
              <el-button size="small" text @click="$router.push('/clusters')">
                管理集群
              </el-button>
            </div>

            <div class="cluster-list">
              <div
                v-for="cluster in availableClusters"
                :key="cluster.id"
                class="cluster-item"
                :class="{
                  'cluster-current': cluster.id === currentClusterId,
                  'cluster-disabled': cluster.status !== 'active',
                }"
                @click="switchCluster(cluster.id)"
              >
                <div class="cluster-item-info">
                  <div class="cluster-item-name">{{ cluster.name }}</div>
                  <div class="cluster-item-meta">
                    <el-tag
                      :type="cluster.status === 'active' ? 'success' : 'danger'"
                      size="small"
                    >
                      {{ getStatusText(cluster.status) }}
                    </el-tag>
                    <span class="cluster-item-type">{{
                      getClusterTypeText(cluster.cluster_type)
                    }}</span>
                  </div>
                </div>
                <div
                  class="cluster-item-indicator"
                  v-if="cluster.id === currentClusterId"
                >
                  <el-icon><Check /></el-icon>
                </div>
              </div>
            </div>

            <div class="dropdown-footer" v-if="availableClusters.length === 0">
              <el-empty description="暂无可用集群" :image-size="60">
                <el-button
                  size="small"
                  type="primary"
                  @click="$router.push('/clusters')"
                >
                  添加集群
                </el-button>
              </el-empty>
            </div>
          </div>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { Connection, ArrowDown, Check } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { clustersApi } from "@/api/clusters";
import { useMonitoringStore } from "@/stores/monitoring";
import { useDashboardStore } from "@/stores/dashboard";

interface Cluster {
  id: number;
  name: string;
  cluster_type: string;
  status: string;
}

const emit = defineEmits<{
  clusterChanged: [clusterId: number];
}>();

const router = useRouter();
const monitoringStore = useMonitoringStore();
const dashboardStore = useDashboardStore();

const clusters = ref<Cluster[]>([]);
const loading = ref(false);

const currentClusterId = computed(
  () => monitoringStore.settings.selectedCluster,
);

const currentCluster = computed(() => {
  return clusters.value.find((c) => c.id === currentClusterId.value);
});

const availableClusters = computed(() => {
  return clusters.value.filter((c) => c.status === "active");
});

const loadClusters = async () => {
  loading.value = true;
  try {
    clusters.value = await clustersApi.list();
  } catch (error) {
    console.error("Failed to load clusters:", error);
    ElMessage.error("加载集群列表失败");
  } finally {
    loading.value = false;
  }
};

const switchCluster = async (clusterId: number) => {
  if (clusterId === currentClusterId.value) return;

  const cluster = clusters.value.find((c) => c.id === clusterId);
  if (!cluster || cluster.status !== "active") {
    ElMessage.warning("该集群当前不可用");
    return;
  }

  try {
    // 更新选中的集群
    monitoringStore.setSelectedCluster(clusterId);

    // 重新加载仪表盘数据
    await dashboardStore.loadAllData(clusterId);

    // 发出集群变更事件
    emit("clusterChanged", clusterId);

    ElMessage.success(`已切换到集群：${cluster.name}`);
  } catch (error) {
    console.error("Failed to switch cluster:", error);
    ElMessage.error("切换集群失败");
  }
};

const getStatusText = (status?: string): string => {
  const statusMap: Record<string, string> = {
    active: "正常",
    inactive: "停用",
    error: "异常",
  };
  return statusMap[status || "inactive"] || "未知";
};

const getClusterTypeText = (type?: string): string => {
  const typeMap: Record<string, string> = {
    cdp: "CDP",
    cdh: "CDH",
    hdp: "HDP",
    apache: "Apache",
  };
  return typeMap[type || ""] || type || "";
};

// 监听当前集群ID变化，重新加载集群列表
watch(
  () => currentClusterId.value,
  () => {
    if (clusters.value.length === 0) {
      loadClusters();
    }
  },
  { immediate: true },
);

onMounted(() => {
  loadClusters();
});
</script>

<style scoped>
.cluster-switcher {
  position: relative;
}

/* 当前集群显示 */
.current-cluster {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-primary);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-normal);
  min-width: 280px;
}

.current-cluster:hover {
  border-color: var(--primary-300);
  box-shadow: var(--elevation-1);
}

.current-cluster.has-error {
  border-color: var(--danger-300);
  background: var(--danger-50);
}

.cluster-icon {
  color: var(--primary-500);
  font-size: var(--text-lg);
  flex-shrink: 0;
}

.current-cluster.has-error .cluster-icon {
  color: var(--danger-500);
}

.cluster-info {
  flex: 1;
  min-width: 0;
}

.cluster-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--gray-900);
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cluster-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-1);
}

.cluster-type {
  font-size: var(--text-xs);
  color: var(--gray-500);
}

.dropdown-arrow {
  color: var(--gray-400);
  font-size: var(--text-sm);
  flex-shrink: 0;
}

/* 下拉菜单 */
.cluster-dropdown {
  min-width: 320px;
  max-height: 400px;
}

.dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-4) var(--space-3);
  border-bottom: 1px solid var(--gray-100);
}

.dropdown-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--gray-900);
}

/* 集群列表 */
.cluster-list {
  max-height: 280px;
  overflow-y: auto;
}

.cluster-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.cluster-item:hover:not(.cluster-disabled) {
  background: var(--gray-50);
}

.cluster-item.cluster-current {
  background: var(--primary-50);
  color: var(--primary-700);
}

.cluster-item.cluster-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cluster-item-info {
  flex: 1;
  min-width: 0;
}

.cluster-item-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--gray-900);
  line-height: 1.2;
  margin-bottom: var(--space-1);
}

.cluster-item.cluster-current .cluster-item-name {
  color: var(--primary-700);
}

.cluster-item-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.cluster-item-type {
  font-size: var(--text-xs);
  color: var(--gray-500);
}

.cluster-item-indicator {
  color: var(--primary-500);
  font-size: var(--text-sm);
  flex-shrink: 0;
}

/* 底部 */
.dropdown-footer {
  padding: var(--space-4);
  text-align: center;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .current-cluster {
    min-width: 240px;
  }

  .cluster-dropdown {
    min-width: 280px;
  }
}
</style>
