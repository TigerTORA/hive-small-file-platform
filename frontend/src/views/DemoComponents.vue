<template>
  <div class="demo-page">
    <div class="demo-header">
      <h1>DataNova 企业级组件库</h1>
      <p>展示升级后的Cloudera风格UI组件体系</p>
    </div>

    <!-- 指标卡片演示 -->
    <section class="demo-section">
      <h2>指标卡片组件</h2>
      <div class="cloudera-metrics-grid">
        <div class="cloudera-metric-card">
          <div class="metric-header">
            <div class="metric-icon primary">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <div class="metric-status">
              <div class="status-dot success"></div>
              <span class="metric-trend up">+12%</span>
            </div>
          </div>
          <div class="metric-value">1,234</div>
          <div class="metric-label">总表数</div>
        </div>

        <div class="cloudera-metric-card">
          <div class="metric-header">
            <div class="metric-icon warning">
              <el-icon><Warning /></el-icon>
            </div>
            <div class="metric-status">
              <span class="cloudera-tag warning">警告</span>
            </div>
          </div>
          <div class="metric-value">56</div>
          <div class="metric-label">问题表</div>
        </div>

        <div class="cloudera-metric-card">
          <div class="metric-header">
            <div class="metric-icon danger">
              <el-icon><Document /></el-icon>
            </div>
            <div class="metric-status">
              <span class="metric-trend down">-8%</span>
            </div>
          </div>
          <div class="metric-value">89.2K</div>
          <div class="metric-label">小文件数</div>
        </div>

        <div class="cloudera-metric-card">
          <div class="metric-header">
            <div class="metric-icon success">
              <el-icon><Connection /></el-icon>
            </div>
            <div class="metric-status">
              <div class="status-dot success"></div>
              <span>运行中</span>
            </div>
          </div>
          <div class="metric-value">集群-01</div>
          <div class="metric-label">集群状态</div>
        </div>
      </div>
    </section>

    <!-- 按钮组件演示 -->
    <section class="demo-section">
      <h2>按钮组件</h2>
      <div class="button-demo">
        <el-button class="cloudera-btn primary">主要按钮</el-button>
        <el-button class="cloudera-btn secondary">次要按钮</el-button>
        <el-button class="cloudera-btn success">成功按钮</el-button>
        <el-button class="cloudera-btn warning">警告按钮</el-button>
        <el-button class="cloudera-btn danger">危险按钮</el-button>
      </div>
    </section>

    <!-- 标签组件演示 -->
    <section class="demo-section">
      <h2>标签组件</h2>
      <div class="tag-demo">
        <span class="cloudera-tag success">成功</span>
        <span class="cloudera-tag warning">警告</span>
        <span class="cloudera-tag danger">错误</span>
        <span class="cloudera-tag info">信息</span>
      </div>
    </section>

    <!-- 表格组件演示 -->
    <section class="demo-section">
      <h2>表格组件</h2>
      <div class="cloudera-table">
        <el-table :data="tableData" stripe>
          <el-table-column prop="name" label="表名" width="200" />
          <el-table-column prop="database" label="数据库" width="150" />
          <el-table-column prop="size" label="大小" width="120" />
          <el-table-column prop="files" label="文件数" width="100" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <span class="cloudera-tag" :class="row.statusType">{{
                row.status
              }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <!-- 状态指示器演示 -->
    <section class="demo-section">
      <h2>状态指示器</h2>
      <div class="status-demo">
        <div class="status-item">
          <div class="status-dot success"></div>
          <span>健康状态</span>
        </div>
        <div class="status-item">
          <div class="status-dot warning"></div>
          <span>警告状态</span>
        </div>
        <div class="status-item">
          <div class="status-dot danger"></div>
          <span>错误状态</span>
        </div>
        <div class="status-item">
          <div class="status-dot info"></div>
          <span>信息状态</span>
        </div>
      </div>
    </section>

    <!-- 玻璃效果卡片演示 -->
    <section class="demo-section">
      <h2>玻璃效果卡片</h2>
      <div class="glass-demo">
        <div class="glass-card hover-lift">
          <h3>玻璃效果卡片</h3>
          <p>
            这是一个带有玻璃形态效果的卡片组件，具有毛玻璃背景和现代化的视觉效果。
          </p>
          <el-button class="cloudera-btn primary">了解更多</el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import {
  TrendCharts,
  Warning,
  Document,
  Connection,
} from "@element-plus/icons-vue";

const tableData = ref([
  {
    name: "user_behavior_logs",
    database: "analytics",
    size: "2.3 GB",
    files: 1247,
    status: "正常",
    statusType: "success",
  },
  {
    name: "transaction_records",
    database: "finance",
    size: "856 MB",
    files: 523,
    status: "警告",
    statusType: "warning",
  },
  {
    name: "system_logs",
    database: "monitoring",
    size: "4.1 GB",
    files: 2891,
    status: "错误",
    statusType: "danger",
  },
  {
    name: "customer_data",
    database: "crm",
    size: "1.8 GB",
    files: 892,
    status: "正常",
    statusType: "success",
  },
]);
</script>

<style scoped>
.demo-page {
  padding: var(--space-6);
  min-height: calc(100vh - 64px);
  overflow-y: auto;
  background: var(--bg-gradient);
}

.demo-header {
  text-align: center;
  margin-bottom: var(--space-8);
  padding: var(--space-8);
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  border: 1px solid var(--gray-200);
  box-shadow: var(--elevation-2);
}

.demo-header h1 {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--gray-900);
  margin-bottom: var(--space-3);
}

.demo-header p {
  font-size: var(--text-lg);
  color: var(--gray-600);
  margin: 0;
}

.demo-section {
  margin-bottom: var(--space-10);
  padding: var(--space-6);
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  border: 1px solid var(--gray-200);
  box-shadow: var(--elevation-1);
}

.demo-section h2 {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-3);
  border-bottom: 2px solid var(--primary-500);
}

.button-demo {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.tag-demo {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.status-demo {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
}

.status-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--gray-50);
  border-radius: var(--radius-lg);
  border: 1px solid var(--gray-200);
}

.glass-demo {
  padding: var(--space-8);
  background: linear-gradient(
    135deg,
    var(--primary-100) 0%,
    var(--primary-200) 100%
  );
  border-radius: var(--radius-xl);
  display: flex;
  justify-content: center;
}

.glass-demo .glass-card {
  max-width: 400px;
  padding: var(--space-6);
  text-align: center;
}

.glass-demo h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
  margin-bottom: var(--space-3);
}

.glass-demo p {
  color: var(--gray-700);
  margin-bottom: var(--space-6);
  line-height: var(--leading-relaxed);
}

/* 响应式适配 */
@media (max-width: 768px) {
  .demo-page {
    padding: var(--space-4);
  }

  .demo-header {
    padding: var(--space-6);
  }

  .demo-section {
    padding: var(--space-4);
  }

  .button-demo {
    flex-direction: column;
  }

  .status-demo {
    grid-template-columns: 1fr;
  }
}
</style>
