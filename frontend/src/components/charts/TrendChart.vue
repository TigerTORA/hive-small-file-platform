<template>
  <div class="trend-chart">
    <div class="chart-header" v-if="showHeader">
      <div class="header-left">
        <h3 class="chart-title">{{ title }}</h3>
        <p class="chart-subtitle" v-if="subtitle">{{ subtitle }}</p>
      </div>
      <div class="header-right">
        <el-radio-group
          v-model="selectedPeriod"
          size="small"
          @change="handlePeriodChange"
        >
          <el-radio-button value="7">7天</el-radio-button>
          <el-radio-button value="30">30天</el-radio-button>
          <el-radio-button value="90">90天</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <div class="chart-container" :style="containerStyle">
      <div v-if="loading" class="chart-loading">
        <el-skeleton animated>
          <template #template>
            <el-skeleton-item
              variant="rect"
              style="width: 100%; height: 100%"
            />
          </template>
        </el-skeleton>
      </div>

      <div v-else-if="error" class="chart-error">
        <el-empty description="数据加载失败">
          <el-button type="primary" @click="$emit('refresh')"
            >重新加载</el-button
          >
        </el-empty>
      </div>

      <v-chart
        v-else
        class="trend-echarts"
        :option="chartOption"
        :loading="loading"
        autoresize
        @click="handleChartClick"
      />
    </div>

    <div class="chart-footer" v-if="showFooter">
      <div class="chart-legend">
        <div class="legend-item" v-for="item in legendItems" :key="item.name">
          <span
            class="legend-color"
            :style="{ backgroundColor: item.color }"
          ></span>
          <span class="legend-text">{{ item.name }}</span>
          <span class="legend-value">{{ item.value }}</span>
        </div>
      </div>

      <div class="chart-actions">
        <el-button-group size="small">
          <el-button @click="handleExport" :loading="exporting">
            <el-icon><Download /></el-icon>
          </el-button>
          <el-button @click="handleFullscreen">
            <el-icon><FullScreen /></el-icon>
          </el-button>
          <el-button @click="$emit('refresh')" :loading="refreshing">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </el-button-group>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, BarChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DataZoomComponent,
  ToolboxComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import { Download, FullScreen, Refresh } from "@element-plus/icons-vue";
import { useCharts } from "@/composables/useCharts";
import { useMonitoringStore } from "@/stores/monitoring";
import type { TrendPoint } from "@/api/dashboard";

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  DataZoomComponent,
  ToolboxComponent,
]);

interface Props {
  data: TrendPoint[];
  title?: string;
  subtitle?: string;
  height?: number;
  showHeader?: boolean;
  showFooter?: boolean;
  loading?: boolean;
  error?: string | null;
  refreshing?: boolean;
  exporting?: boolean;
  theme?: "light" | "dark";
}

const props = withDefaults(defineProps<Props>(), {
  title: "小文件趋势分析",
  subtitle: "显示文件数量和小文件占比的变化趋势",
  height: 400,
  showHeader: true,
  showFooter: true,
  loading: false,
  error: null,
  refreshing: false,
  exporting: false,
  theme: "light",
});

const emit = defineEmits<{
  refresh: [];
  export: [];
  fullscreen: [];
  "period-change": [period: number];
  "chart-click": [params: any];
}>();

const { getTrendChartOption } = useCharts();
const monitoringStore = useMonitoringStore();

const selectedPeriod = ref<string>("30");

// 计算属性
const containerStyle = computed(() => ({
  height: `${props.height}px`,
  position: "relative",
}));

const chartOption = computed(() => {
  if (!props.data || props.data.length === 0) {
    return {
      title: {
        text: "暂无数据",
        left: "center",
        top: "center",
        textStyle: {
          fontSize: 14,
          color: "#999",
        },
      },
    };
  }

  return getTrendChartOption(props.data);
});

const legendItems = computed(() => {
  if (!props.data || props.data.length === 0) return [];

  const latest = props.data[props.data.length - 1];
  return [
    {
      name: "总文件数",
      color: monitoringStore.getChartColor(0),
      value: monitoringStore.formatNumber(latest.total_files),
    },
    {
      name: "小文件数",
      color: monitoringStore.getChartColor(3),
      value: monitoringStore.formatNumber(latest.small_files),
    },
    {
      name: "小文件占比",
      color: monitoringStore.getChartColor(2),
      value: `${latest.ratio.toFixed(1)}%`,
    },
  ];
});

// 方法
function handlePeriodChange(value: string) {
  emit("period-change", parseInt(value));
}

function handleExport() {
  emit("export");
}

function handleFullscreen() {
  emit("fullscreen");
}

function handleChartClick(params: any) {
  emit("chart-click", params);
}

// 监听主题变化
watch(
  () => monitoringStore.settings.theme,
  () => {
    // 主题变化时图表会自动重新渲染
  },
  { immediate: true },
);
</script>

<style scoped>
.trend-chart {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  transition: all 0.3s ease;
}

.trend-chart:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 24px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.header-left {
  flex: 1;
}

.chart-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
}

.chart-subtitle {
  margin: 4px 0 0;
  font-size: 14px;
  color: #6b7280;
  line-height: 1.4;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chart-container {
  padding: 16px 24px;
  background: #fafafa;
}

.chart-loading,
.chart-error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: white;
  border-radius: 8px;
}

.trend-echarts {
  width: 100%;
  height: 100%;
  background: white;
  border-radius: 8px;
}

.chart-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #f9fafb;
  border-top: 1px solid #f0f0f0;
}

.chart-legend {
  display: flex;
  gap: 24px;
  align-items: center;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-text {
  color: #374151;
  font-weight: 500;
}

.legend-value {
  color: #6b7280;
  font-weight: 600;
}

.chart-actions {
  display: flex;
  align-items: center;
}

/* 暗色主题 */
.trend-chart[data-theme="dark"] {
  background: #1f2937;
  color: white;
}

.trend-chart[data-theme="dark"] .chart-header {
  border-bottom-color: #374151;
}

.trend-chart[data-theme="dark"] .chart-title {
  color: white;
}

.trend-chart[data-theme="dark"] .chart-subtitle {
  color: #d1d5db;
}

.trend-chart[data-theme="dark"] .chart-container {
  background: #111827;
}

.trend-chart[data-theme="dark"] .trend-echarts {
  background: #1f2937;
}

.trend-chart[data-theme="dark"] .chart-footer {
  background: #111827;
  border-top-color: #374151;
}

.trend-chart[data-theme="dark"] .legend-text {
  color: #d1d5db;
}

.trend-chart[data-theme="dark"] .legend-value {
  color: #9ca3af;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chart-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }

  .header-right {
    width: 100%;
    justify-content: flex-start;
  }

  .chart-footer {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }

  .chart-legend {
    width: 100%;
    justify-content: flex-start;
    gap: 16px;
  }

  .chart-actions {
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .chart-header {
    padding: 16px 16px 12px;
  }

  .chart-container {
    padding: 12px 16px;
  }

  .chart-footer {
    padding: 12px 16px;
  }

  .chart-title {
    font-size: 16px;
  }

  .chart-subtitle {
    font-size: 13px;
  }

  .legend-item {
    font-size: 13px;
  }
}
</style>
