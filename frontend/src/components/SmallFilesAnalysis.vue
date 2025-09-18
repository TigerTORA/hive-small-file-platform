<template>
  <div class="analysis-view">
    <div class="analysis-header">
      <h3>小文件分析报告</h3>
      <el-button @click="refreshAnalysis">
        <el-icon><Refresh /></el-icon>
        刷新分析
      </el-button>
    </div>

    <div class="analysis-cards">
      <el-card class="summary-card">
        <template #header>
          <span>分析概览</span>
        </template>
        <div class="summary-stats">
          <div class="stat-item">
            <span class="stat-value">{{ analysis.total_tables }}</span>
            <span class="stat-label">总表数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-warning">{{
              analysis.affected_tables
            }}</span>
            <span class="stat-label">受影响表数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value text-danger">{{
              analysis.total_small_files
            }}</span>
            <span class="stat-label">小文件总数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{
              formatSize(analysis.potential_savings)
            }}</span>
            <span class="stat-label">潜在节省空间</span>
          </div>
        </div>
      </el-card>

      <el-card class="chart-card">
        <template #header>
          <span>文件分布</span>
        </template>
        <div class="chart-placeholder">
          <!-- TODO: Add chart component -->
          <p>图表组件开发中...</p>
        </div>
      </el-card>
    </div>

    <el-card class="table-analysis">
      <template #header>
        <span>表级别分析</span>
      </template>

      <el-table :data="analysis.table_details" v-loading="loading" stripe>
        <el-table-column prop="database_name" label="数据库" width="120" />
        <el-table-column prop="table_name" label="表名" min-width="150" />
        <el-table-column
          prop="total_files"
          label="总文件数"
          width="100"
          align="right"
        />
        <el-table-column
          prop="small_files"
          label="小文件数"
          width="100"
          align="right"
        >
          <template #default="{ row }">
            <span class="text-warning">{{ row.small_files }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="small_file_ratio"
          label="小文件比例"
          width="120"
          align="right"
        >
          <template #default="{ row }">
            {{ (row.small_file_ratio * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column
          prop="total_size"
          label="总大小"
          width="120"
          align="right"
        >
          <template #default="{ row }">
            {{ formatSize(row.total_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优化优先级" width="120">
          <template #default="{ row }">
            <el-tag :type="getPriorityType(row.priority)">
              {{ getPriorityText(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="optimizeTable(row)">
              优化
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { tablesApi } from "@/api/tables";

interface Props {
  clusterId: number;
}

const props = defineProps<Props>();

// Data
const loading = ref(false);
const analysis = ref({
  total_tables: 0,
  affected_tables: 0,
  total_small_files: 0,
  potential_savings: 0,
  table_details: [],
});

// Methods
const loadAnalysis = async () => {
  loading.value = true;
  try {
    const response = await tablesApi.getSmallFilesAnalysis(props.clusterId);
    analysis.value = response;
  } catch (error) {
    console.error("Failed to load analysis:", error);
    ElMessage.error("加载分析报告失败");
  } finally {
    loading.value = false;
  }
};

const refreshAnalysis = () => {
  loadAnalysis();
};

const optimizeTable = async (table: any) => {
  try {
    // TODO: Implement table optimization
    ElMessage.success(`开始优化表 ${table.table_name}`);
  } catch (error) {
    console.error("Failed to optimize table:", error);
    ElMessage.error("优化失败");
  }
};

const getPriorityType = (priority: string) => {
  const typeMap = {
    high: "danger",
    medium: "warning",
    low: "info",
  };
  return typeMap[priority as keyof typeof typeMap] || "info";
};

const getPriorityText = (priority: string) => {
  const textMap = {
    high: "高",
    medium: "中",
    low: "低",
  };
  return textMap[priority as keyof typeof textMap] || priority;
};

const formatSize = (bytes: number): string => {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
};

onMounted(() => {
  loadAnalysis();
});
</script>

<style scoped>
.analysis-view {
  height: 100%;
}

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.analysis-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 5px;
}

.stat-label {
  color: #909399;
  font-size: 14px;
}

.text-warning {
  color: #e6a23c;
}

.text-danger {
  color: #f56c6c;
}

.chart-card {
  min-height: 200px;
}

.chart-placeholder {
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.table-analysis {
  margin-top: 20px;
}

@media (max-width: 768px) {
  .analysis-cards {
    grid-template-columns: 1fr;
  }

  .summary-stats {
    grid-template-columns: 1fr;
  }
}
</style>
