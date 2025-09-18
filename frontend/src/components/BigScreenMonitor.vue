<template>
  <div class="big-screen-monitor" :class="{ 'fullscreen-mode': isFullscreen }">
    <!-- 大屏头部 -->
    <div class="big-screen-header">
      <div class="header-left">
        <div class="logo-section">
          <el-icon class="logo-icon"><Monitor /></el-icon>
          <h1 class="system-title">Hive 小文件治理平台</h1>
          <span class="subtitle">实时监控大屏</span>
        </div>
      </div>

      <div class="header-center">
        <div class="current-time" data-testid="big-screen-time">
          {{ currentTime }}
        </div>
      </div>

      <div class="header-right">
        <div class="cluster-selector">
          <el-select
            v-model="selectedCluster"
            placeholder="选择集群"
            size="large"
            style="width: 200px"
            @change="handleClusterChange"
          >
            <el-option
              v-for="cluster in availableClusters"
              :key="cluster.id"
              :label="cluster.name"
              :value="cluster.id"
            />
          </el-select>
        </div>

        <el-button
          :icon="Close"
          type="danger"
          size="large"
          circle
          @click="exitBigScreen"
          title="退出大屏模式"
        />
      </div>
    </div>

    <!-- 大屏主要内容区域 -->
    <div class="big-screen-content">
      <!-- 顶部关键指标 -->
      <div class="top-metrics-row">
        <div
          v-for="(metric, index) in keyMetrics"
          :key="metric.key"
          class="metric-card"
          :class="`metric-${metric.type}`"
          :style="{
            animationDelay: `${index * 0.1}s`,
            '--metric-color': getMetricColor(metric.type),
          }"
        >
          <div class="metric-icon">
            <component :is="metric.icon" />
          </div>
          <div class="metric-content">
            <div class="metric-value">{{ metric.value }}</div>
            <div class="metric-label">{{ metric.label }}</div>
            <div
              v-if="metric.trend"
              class="metric-trend"
              :class="metric.trend.type"
            >
              <component :is="metric.trend.icon" />
              <span>{{ metric.trend.value }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 中间图表区域 -->
      <div class="charts-section">
        <!-- 左侧主图表 -->
        <div class="main-chart-container">
          <div class="chart-header">
            <h3>小文件分布趋势</h3>
            <div class="chart-controls">
              <el-radio-group v-model="chartTimeRange" size="small">
                <el-radio-button label="1h">最近1小时</el-radio-button>
                <el-radio-button label="24h">最近24小时</el-radio-button>
                <el-radio-button label="7d">最近7天</el-radio-button>
              </el-radio-group>
            </div>
          </div>
          <div ref="mainChartRef" class="main-chart"></div>
        </div>

        <!-- 右侧辅助图表 -->
        <div class="side-charts">
          <!-- 集群状态分布 -->
          <div class="side-chart-item">
            <div class="chart-header">
              <h4>集群状态分布</h4>
            </div>
            <div ref="clusterStatusChartRef" class="side-chart"></div>
          </div>

          <!-- 数据库TOP10 -->
          <div class="side-chart-item">
            <div class="chart-header">
              <h4>小文件数量 TOP10 数据库</h4>
            </div>
            <div ref="topDatabaseChartRef" class="side-chart"></div>
          </div>
        </div>
      </div>

      <!-- 底部实时信息 -->
      <div class="bottom-info-section">
        <!-- 实时任务状态 -->
        <div class="real-time-tasks">
          <div class="section-header">
            <h3>实时任务状态</h3>
            <div class="refresh-indicator" :class="{ active: isRefreshing }">
              <el-icon><Refresh /></el-icon>
              <span>自动刷新</span>
            </div>
          </div>
          <div class="tasks-grid">
            <div
              v-for="task in recentTasks"
              :key="task.id"
              class="task-card"
              :class="`status-${task.status}`"
            >
              <div class="task-type">{{ task.type_display }}</div>
              <div class="task-target">{{ task.target_info }}</div>
              <div class="task-status">
                <el-tag :type="getTaskStatusType(task.status)" size="small">
                  {{ task.status_display }}
                </el-tag>
              </div>
              <div class="task-progress">
                <el-progress
                  v-if="task.status === 'running'"
                  :percentage="task.progress || 0"
                  :stroke-width="4"
                  :show-text="false"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- 系统运行状态 -->
        <div class="system-status">
          <div class="section-header">
            <h3>系统运行状态</h3>
          </div>
          <div class="status-indicators">
            <div class="status-item">
              <div class="indicator online"></div>
              <span>服务状态：正常</span>
            </div>
            <div class="status-item">
              <div class="indicator" :class="wsConnectionStatus"></div>
              <span
                >WebSocket：{{
                  wsConnectionStatus === "online" ? "已连接" : "断开"
                }}</span
              >
            </div>
            <div class="status-item">
              <div class="indicator online"></div>
              <span>数据库：正常</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import { useRouter } from "vue-router";
import {
  Monitor,
  Close,
  Refresh,
  Grid,
  Coin,
  Document,
  ArrowUp,
  ArrowDown,
} from "@element-plus/icons-vue";
import * as echarts from "echarts";
import { useDashboardStore } from "@/stores/dashboard";
import { useMonitoringStore } from "@/stores/monitoring";
import { FeatureManager } from "@/utils/feature-flags";

// Props
interface Props {
  clusterId?: string;
}

const props = withDefaults(defineProps<Props>(), {
  clusterId: "",
});

// Router
const router = useRouter();

// Stores
const dashboardStore = useDashboardStore();
const monitoringStore = useMonitoringStore();

// 响应式数据
const isFullscreen = ref(true);
const currentTime = ref("");
const selectedCluster = ref(props.clusterId || "");
const chartTimeRange = ref("24h");
const isRefreshing = ref(false);
const wsConnectionStatus = ref<"online" | "offline">("online");

// Chart refs
const mainChartRef = ref<HTMLElement>();
const clusterStatusChartRef = ref<HTMLElement>();
const topDatabaseChartRef = ref<HTMLElement>();

// Chart instances
let mainChart: echarts.ECharts | null = null;
let clusterStatusChart: echarts.ECharts | null = null;
let topDatabaseChart: echarts.ECharts | null = null;

// 模拟集群数据
const availableClusters = ref([
  { id: "cluster-1", name: "生产集群-01" },
  { id: "cluster-2", name: "测试集群-01" },
  { id: "cluster-3", name: "开发集群-01" },
]);

// 计算属性 - 关键指标
const keyMetrics = computed(() => {
  const summary = dashboardStore.summary;
  return [
    {
      key: "total_tables",
      label: "总表数",
      value: formatNumber(summary.total_tables),
      icon: Grid,
      type: "primary",
      trend: { type: "up", icon: ArrowUp, value: "+5.2%" },
    },
    {
      key: "small_files",
      label: "小文件总数",
      value: formatNumber(summary.total_small_files),
      icon: Document,
      type: "warning",
      trend: { type: "down", icon: ArrowDown, value: "-2.1%" },
    },
    {
      key: "total_size",
      label: "总存储大小",
      value: formatFileSize(summary.total_size_bytes),
      icon: Coin,
      type: "info",
      trend: { type: "up", icon: ArrowUp, value: "+8.3%" },
    },
    {
      key: "small_file_ratio",
      label: "小文件率",
      value: `${summary.small_file_ratio}%`,
      icon: ArrowUp,
      type: summary.small_file_ratio > 30 ? "danger" : "success",
      trend: { type: "down", icon: ArrowDown, value: "-1.5%" },
    },
  ];
});

// 计算属性 - 最近任务
const recentTasks = computed(() => {
  return dashboardStore.recentTasks.slice(0, 8).map((task) => ({
    ...task,
    type_display: task.type === "scan" ? "扫描任务" : "合并任务",
    target_info: `${task.database_name}.${task.table_name}`,
    status_display: getStatusDisplay(task.status),
    progress: Math.floor(Math.random() * 100), // 模拟进度
  }));
});

// 时间更新
const updateTime = () => {
  const now = new Date();
  currentTime.value = now.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
};

// 工具函数
const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + "M";
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + "K";
  }
  return num.toString();
};

const formatFileSize = (bytes: number): string => {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`;
};

const getMetricColor = (type: string): string => {
  const colors = {
    primary: "var(--hive-primary)",
    success: "var(--hive-success)",
    warning: "var(--hive-warning)",
    danger: "var(--hive-danger)",
    info: "var(--hive-info)",
  };
  return colors[type as keyof typeof colors] || colors.primary;
};

const getStatusDisplay = (status: string): string => {
  const statusMap = {
    pending: "待执行",
    running: "执行中",
    completed: "已完成",
    failed: "失败",
    cancelled: "已取消",
  };
  return statusMap[status as keyof typeof statusMap] || status;
};

const getTaskStatusType = (status: string): string => {
  const typeMap = {
    pending: "info",
    running: "warning",
    completed: "success",
    failed: "danger",
    cancelled: "info",
  };
  return typeMap[status as keyof typeof typeMap] || "info";
};

// 事件处理
const handleClusterChange = (clusterId: string) => {
  selectedCluster.value = clusterId;
  dashboardStore.loadAllData(clusterId);
  refreshCharts();
};

const exitBigScreen = () => {
  FeatureManager.disable("fullscreenMode");
  router.push("/");
};

// 图表相关方法
const initCharts = async () => {
  await nextTick();

  // 主图表
  if (mainChartRef.value) {
    mainChart = echarts.init(mainChartRef.value);
    updateMainChart();
  }

  // 集群状态图表
  if (clusterStatusChartRef.value) {
    clusterStatusChart = echarts.init(clusterStatusChartRef.value);
    updateClusterStatusChart();
  }

  // TOP数据库图表
  if (topDatabaseChartRef.value) {
    topDatabaseChart = echarts.init(topDatabaseChartRef.value);
    updateTopDatabaseChart();
  }

  // 监听窗口大小变化
  window.addEventListener("resize", handleResize);
};

const updateMainChart = () => {
  if (!mainChart) return;

  const option = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "cross",
      },
    },
    legend: {
      data: ["小文件数量", "合并后文件数量"],
      textStyle: {
        color: "#fff",
      },
    },
    grid: {
      left: "5%",
      right: "5%",
      bottom: "10%",
      top: "20%",
    },
    xAxis: {
      type: "category",
      data: generateTimeLabels(),
      axisLine: {
        lineStyle: {
          color: "#4a5568",
        },
      },
      axisLabel: {
        color: "#a0aec0",
      },
    },
    yAxis: {
      type: "value",
      axisLine: {
        lineStyle: {
          color: "#4a5568",
        },
      },
      axisLabel: {
        color: "#a0aec0",
      },
      splitLine: {
        lineStyle: {
          color: "#2d3748",
        },
      },
    },
    series: [
      {
        name: "小文件数量",
        type: "line",
        data: generateMockData(),
        smooth: true,
        lineStyle: {
          color: "#f56565",
          width: 3,
        },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(245, 101, 101, 0.6)" },
              { offset: 1, color: "rgba(245, 101, 101, 0.1)" },
            ],
          },
        },
      },
      {
        name: "合并后文件数量",
        type: "line",
        data: generateMockData(0.3),
        smooth: true,
        lineStyle: {
          color: "#48bb78",
          width: 3,
        },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(72, 187, 120, 0.6)" },
              { offset: 1, color: "rgba(72, 187, 120, 0.1)" },
            ],
          },
        },
      },
    ],
  };

  mainChart.setOption(option);
};

const updateClusterStatusChart = () => {
  if (!clusterStatusChart) return;

  const option = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
    },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        center: ["50%", "50%"],
        data: [
          { value: 2, name: "正常", itemStyle: { color: "#48bb78" } },
          { value: 1, name: "警告", itemStyle: { color: "#ed8936" } },
          { value: 0, name: "故障", itemStyle: { color: "#f56565" } },
        ],
        label: {
          color: "#fff",
          fontSize: 12,
        },
      },
    ],
  };

  clusterStatusChart.setOption(option);
};

const updateTopDatabaseChart = () => {
  if (!topDatabaseChart) return;

  const option = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
      },
    },
    grid: {
      left: "15%",
      right: "5%",
      bottom: "10%",
      top: "10%",
    },
    xAxis: {
      type: "value",
      axisLine: {
        lineStyle: {
          color: "#4a5568",
        },
      },
      axisLabel: {
        color: "#a0aec0",
      },
      splitLine: {
        lineStyle: {
          color: "#2d3748",
        },
      },
    },
    yAxis: {
      type: "category",
      data: ["db_logs", "user_data", "temp_data", "backup_db", "analytics"],
      axisLine: {
        lineStyle: {
          color: "#4a5568",
        },
      },
      axisLabel: {
        color: "#a0aec0",
      },
    },
    series: [
      {
        type: "bar",
        data: [1234, 987, 756, 543, 321],
        itemStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: "#667eea" },
              { offset: 1, color: "#764ba2" },
            ],
          },
        },
        barWidth: "60%",
      },
    ],
  };

  topDatabaseChart.setOption(option);
};

const generateTimeLabels = (): string[] => {
  const labels = [];
  const now = new Date();
  const interval =
    chartTimeRange.value === "1h"
      ? 5
      : chartTimeRange.value === "24h"
        ? 60
        : 1440; // 分钟
  const count =
    chartTimeRange.value === "1h"
      ? 12
      : chartTimeRange.value === "24h"
        ? 24
        : 7;

  for (let i = count - 1; i >= 0; i--) {
    const time = new Date(now.getTime() - i * interval * 60 * 1000);
    labels.push(
      time.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
      }),
    );
  }

  return labels;
};

const generateMockData = (factor = 1): number[] => {
  const data = [];
  const baseValue = 1000;

  for (let i = 0; i < 24; i++) {
    const variation = Math.random() * 200 - 100; // -100 到 +100 的随机变化
    data.push(Math.max(0, Math.floor((baseValue + variation) * factor)));
  }

  return data;
};

const refreshCharts = () => {
  updateMainChart();
  updateClusterStatusChart();
  updateTopDatabaseChart();
};

const handleResize = () => {
  if (mainChart) mainChart.resize();
  if (clusterStatusChart) clusterStatusChart.resize();
  if (topDatabaseChart) topDatabaseChart.resize();
};

// 定时器
let timeInterval: NodeJS.Timeout | null = null;
let refreshInterval: NodeJS.Timeout | null = null;

// 生命周期
onMounted(async () => {
  // 启动时间更新
  updateTime();
  timeInterval = setInterval(updateTime, 1000);

  // 启动数据刷新
  refreshInterval = setInterval(() => {
    isRefreshing.value = true;
    setTimeout(() => {
      isRefreshing.value = false;
      refreshCharts();
    }, 1000);
  }, 30000); // 30秒刷新一次

  // 初始化图表
  await initCharts();

  // 加载数据
  if (selectedCluster.value) {
    await dashboardStore.loadAllData(selectedCluster.value);
  }
});

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval);
  if (refreshInterval) clearInterval(refreshInterval);

  if (mainChart) {
    mainChart.dispose();
    mainChart = null;
  }
  if (clusterStatusChart) {
    clusterStatusChart.dispose();
    clusterStatusChart = null;
  }
  if (topDatabaseChart) {
    topDatabaseChart.dispose();
    topDatabaseChart = null;
  }

  window.removeEventListener("resize", handleResize);
});
</script>

<style scoped>
.big-screen-monitor {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #0c1427 0%, #1a202c 50%, #2d3748 100%);
  color: var(--hive-white);
  overflow: hidden;
  position: relative;
}

.big-screen-monitor::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    radial-gradient(
      circle at 20% 20%,
      rgba(64, 158, 255, 0.1) 0%,
      transparent 50%
    ),
    radial-gradient(
      circle at 80% 80%,
      rgba(72, 187, 120, 0.1) 0%,
      transparent 50%
    ),
    radial-gradient(
      circle at 40% 60%,
      rgba(245, 101, 101, 0.05) 0%,
      transparent 50%
    );
  pointer-events: none;
}

.big-screen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--hive-space-6) var(--hive-space-8);
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  position: relative;
  z-index: 10;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: var(--hive-space-4);
}

.logo-icon {
  font-size: 48px;
  color: var(--hive-primary);
  filter: drop-shadow(0 0 10px rgba(64, 158, 255, 0.5));
}

.system-title {
  margin: 0;
  font-size: var(--hive-font-size-3xl);
  font-weight: var(--hive-font-weight-bold);
  background: var(--hive-gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: 0 0 20px rgba(64, 158, 255, 0.3);
}

.subtitle {
  font-size: var(--hive-font-size-lg);
  color: var(--hive-gray-300);
  font-weight: var(--hive-font-weight-medium);
}

.current-time {
  font-size: var(--hive-font-size-2xl);
  font-weight: var(--hive-font-weight-semibold);
  color: var(--hive-white);
  text-align: center;
  padding: var(--hive-space-4) var(--hive-space-6);
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--hive-radius-xl);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: var(--hive-shadow-base);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--hive-space-6);
}

.big-screen-content {
  padding: var(--hive-space-6) var(--hive-space-8);
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  gap: var(--hive-space-6);
  position: relative;
  z-index: 1;
}

/* 顶部指标卡片 */
.top-metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--hive-space-6);
}

.metric-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(15px);
  border-radius: var(--hive-radius-2xl);
  padding: var(--hive-space-6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  gap: var(--hive-space-5);
  transition: var(--hive-transition-all);
  animation: slideInUp 0.6s ease-out forwards;
  transform: translateY(20px);
  opacity: 0;
  position: relative;
  overflow: hidden;
}

.metric-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.1),
    transparent
  );
  transition: left 0.5s ease;
}

.metric-card:hover::before {
  left: 100%;
}

.metric-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  border-color: var(--metric-color);
}

.metric-icon {
  width: 64px;
  height: 64px;
  border-radius: var(--hive-radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  background: linear-gradient(135deg, var(--metric-color), transparent);
  color: var(--hive-white);
  box-shadow: 0 0 20px rgba(var(--metric-color), 0.3);
}

.metric-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--hive-space-1);
}

.metric-value {
  font-size: var(--hive-font-size-3xl);
  font-weight: var(--hive-font-weight-bold);
  color: var(--hive-white);
  line-height: var(--hive-line-height-tight);
}

.metric-label {
  font-size: var(--hive-font-size-sm);
  color: var(--hive-gray-300);
  font-weight: var(--hive-font-weight-medium);
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: var(--hive-space-1);
  font-size: var(--hive-font-size-sm);
  font-weight: var(--hive-font-weight-medium);
}

.metric-trend.up {
  color: var(--hive-success);
}

.metric-trend.down {
  color: var(--hive-danger);
}

/* 图表区域 */
.charts-section {
  flex: 1;
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--hive-space-6);
  min-height: 0;
}

.main-chart-container,
.side-charts {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(15px);
  border-radius: var(--hive-radius-2xl);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: var(--hive-space-6);
}

.side-charts {
  display: flex;
  flex-direction: column;
  gap: var(--hive-space-4);
}

.side-chart-item {
  flex: 1;
  background: rgba(255, 255, 255, 0.03);
  border-radius: var(--hive-radius-xl);
  padding: var(--hive-space-4);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--hive-space-4);
}

.chart-header h3 {
  margin: 0;
  font-size: var(--hive-font-size-xl);
  font-weight: var(--hive-font-weight-semibold);
  color: var(--hive-white);
}

.chart-header h4 {
  margin: 0;
  font-size: var(--hive-font-size-lg);
  font-weight: var(--hive-font-weight-medium);
  color: var(--hive-white);
}

.main-chart,
.side-chart {
  width: 100%;
  height: 300px;
}

.main-chart {
  height: calc(100% - 60px);
}

/* 底部信息区域 */
.bottom-info-section {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--hive-space-6);
  height: 200px;
}

.real-time-tasks,
.system-status {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(15px);
  border-radius: var(--hive-radius-2xl);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: var(--hive-space-5);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--hive-space-4);
}

.section-header h3 {
  margin: 0;
  font-size: var(--hive-font-size-lg);
  font-weight: var(--hive-font-weight-semibold);
  color: var(--hive-white);
}

.refresh-indicator {
  display: flex;
  align-items: center;
  gap: var(--hive-space-2);
  color: var(--hive-gray-400);
  font-size: var(--hive-font-size-sm);
  transition: var(--hive-transition-all);
}

.refresh-indicator.active {
  color: var(--hive-primary);
}

.refresh-indicator.active .el-icon {
  animation: spin 1s linear infinite;
}

.tasks-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--hive-space-3);
  height: calc(100% - 50px);
  overflow-y: auto;
}

.task-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: var(--hive-radius-lg);
  padding: var(--hive-space-3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  gap: var(--hive-space-2);
  transition: var(--hive-transition-all);
}

.task-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--hive-shadow-base);
}

.task-type {
  font-size: var(--hive-font-size-xs);
  font-weight: var(--hive-font-weight-semibold);
  color: var(--hive-primary);
}

.task-target {
  font-size: var(--hive-font-size-xs);
  color: var(--hive-white);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-indicators {
  display: flex;
  flex-direction: column;
  gap: var(--hive-space-4);
  height: calc(100% - 50px);
}

.status-item {
  display: flex;
  align-items: center;
  gap: var(--hive-space-3);
  padding: var(--hive-space-3);
  background: rgba(255, 255, 255, 0.03);
  border-radius: var(--hive-radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.05);
  font-size: var(--hive-font-size-sm);
  color: var(--hive-white);
}

.indicator {
  width: 12px;
  height: 12px;
  border-radius: var(--hive-radius-full);
  flex-shrink: 0;
}

.indicator.online {
  background: var(--hive-success);
  box-shadow: 0 0 10px rgba(72, 187, 120, 0.5);
}

.indicator.offline {
  background: var(--hive-danger);
  box-shadow: 0 0 10px rgba(245, 101, 101, 0.5);
}

/* 动画 */
@keyframes slideInUp {
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 响应式设计 */
@media (max-width: var(--hive-breakpoint-xl)) {
  .top-metrics-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .charts-section {
    grid-template-columns: 1fr;
  }

  .bottom-info-section {
    grid-template-columns: 1fr;
    height: auto;
  }

  .tasks-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: var(--hive-breakpoint-lg)) {
  .big-screen-header {
    flex-direction: column;
    gap: var(--hive-space-4);
    padding: var(--hive-space-4);
  }

  .system-title {
    font-size: var(--hive-font-size-2xl);
  }

  .current-time {
    font-size: var(--hive-font-size-lg);
  }

  .top-metrics-row {
    grid-template-columns: 1fr;
  }

  .tasks-grid {
    grid-template-columns: 1fr;
  }
}
</style>
