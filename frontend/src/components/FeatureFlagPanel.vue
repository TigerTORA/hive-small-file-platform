<template>
  <el-drawer
    v-model="visible"
    title="特性开关管理"
    direction="rtl"
    size="400px"
    class="feature-panel"
  >
    <template #header>
      <div class="panel-header">
        <h3>特性开关管理</h3>
        <el-tag type="info" size="small">开发模式</el-tag>
      </div>
    </template>

    <div class="panel-content">
      <!-- 预设配置 -->
      <el-card class="preset-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><Histogram /></el-icon>
            <span>预设配置</span>
          </div>
        </template>

        <div class="preset-buttons">
          <el-button
            v-for="(preset, key) in presets"
            :key="key"
            :type="currentPreset === key ? 'primary' : 'default'"
            size="small"
            @click="applyPreset(key)"
          >
            {{ preset.name }}
          </el-button>
        </div>
      </el-card>

      <!-- 特性开关列表 -->
      <el-card class="features-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><Operation /></el-icon>
            <span>功能开关</span>
          </div>
        </template>

        <div class="feature-list">
          <div
            v-for="(config, key) in featureConfigs"
            :key="key"
            class="feature-item"
          >
            <div class="feature-info">
              <div class="feature-name">{{ config.name }}</div>
              <div class="feature-desc">{{ config.description }}</div>
            </div>
            <el-switch
              :model-value="features[key]"
              @change="toggleFeature(key, $event)"
              :disabled="config.disabled"
            />
          </div>
        </div>
      </el-card>

      <!-- 配置导入导出 -->
      <el-card class="config-section" shadow="never">
        <template #header>
          <div class="section-header">
            <el-icon><DocumentCopy /></el-icon>
            <span>配置管理</span>
          </div>
        </template>

        <div class="config-actions">
          <el-button @click="exportConfig" :icon="Download" size="small">
            导出配置
          </el-button>
          <el-button
            @click="showImportDialog = true"
            :icon="Upload"
            size="small"
          >
            导入配置
          </el-button>
          <el-button
            @click="resetConfig"
            :icon="RefreshLeft"
            size="small"
            type="warning"
          >
            重置配置
          </el-button>
        </div>

        <div class="current-config">
          <el-text size="small" type="info">
            当前配置：{{ Object.keys(enabledFeatures).length }} /
            {{ Object.keys(features).length }} 个功能启用
          </el-text>
        </div>
      </el-card>
    </div>

    <!-- 导入配置对话框 -->
    <el-dialog
      v-model="showImportDialog"
      title="导入配置"
      width="500px"
      append-to-body
    >
      <el-input
        v-model="importConfigText"
        type="textarea"
        :rows="8"
        placeholder="粘贴配置JSON..."
      />
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="importConfig">导入</el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Histogram,
  Operation,
  DocumentCopy,
  Download,
  Upload,
  RefreshLeft,
} from "@element-plus/icons-vue";
import {
  FeatureManager,
  type FeatureFlags,
  presetConfigs,
} from "@/utils/feature-flags";

interface Props {
  visible: boolean;
  features: FeatureFlags;
}

interface Emits {
  (e: "update:visible", visible: boolean): void;
  (e: "update"): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = computed({
  get: () => props.visible,
  set: (value) => emit("update:visible", value),
});

const showImportDialog = ref(false);
const importConfigText = ref("");
const currentPreset = ref<string | null>(null);

// 预设配置信息
const presets = {
  development: { name: "开发模式", description: "所有功能开启" },
  production: { name: "生产模式", description: "稳定功能" },
  demo: { name: "演示模式", description: "展示效果最佳" },
  minimal: { name: "精简模式", description: "最小功能集" },
};

// 特性配置信息
const featureConfigs: Record<
  keyof FeatureFlags,
  {
    name: string;
    description: string;
    disabled?: boolean;
  }
> = {
  realtimeMonitoring: {
    name: "实时监控",
    description: "启用实时数据监控和刷新",
  },
  advancedCharts: {
    name: "高级图表",
    description: "显示更多图表类型和交互功能",
  },
  demoMode: {
    name: "演示模式",
    description: "使用演示数据，无需真实环境",
  },
  exportReports: {
    name: "导出报告",
    description: "支持PDF和图片导出功能",
  },
  fullscreenMode: {
    name: "全屏模式",
    description: "支持大屏展示模式",
  },
  darkTheme: {
    name: "深色主题",
    description: "启用深色主题界面",
  },
  performanceMonitoring: {
    name: "性能监控",
    description: "显示性能指标和优化建议",
  },
  smartRecommendations: {
    name: "智能建议",
    description: "基于AI的优化建议",
  },
  batchOperations: {
    name: "批量操作",
    description: "支持批量扫描和合并操作",
  },
  websocketUpdates: {
    name: "WebSocket更新",
    description: "实时推送更新（实验性）",
  },
};

// 当前启用的功能
const enabledFeatures = computed(() => {
  return Object.fromEntries(
    Object.entries(props.features).filter(([, enabled]) => enabled),
  );
});

// 切换特性
const toggleFeature = (feature: keyof FeatureFlags, enabled: boolean) => {
  if (enabled) {
    FeatureManager.enable(feature);
  } else {
    FeatureManager.disable(feature);
  }
  emit("update");
  currentPreset.value = null; // 自定义配置时清除预设标记
};

// 应用预设配置
const applyPreset = (preset: keyof typeof presetConfigs) => {
  FeatureManager.setFeatures(presetConfigs[preset]);
  currentPreset.value = preset;
  emit("update");
  ElMessage.success(`已应用${presets[preset].name}配置`);
};

// 导出配置
const exportConfig = () => {
  const config = FeatureManager.exportConfig();
  navigator.clipboard
    .writeText(config)
    .then(() => {
      ElMessage.success("配置已复制到剪贴板");
    })
    .catch(() => {
      // 降级方案
      const textarea = document.createElement("textarea");
      textarea.value = config;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      ElMessage.success("配置已复制到剪贴板");
    });
};

// 导入配置
const importConfig = () => {
  try {
    FeatureManager.importConfig(importConfigText.value);
    emit("update");
    showImportDialog.value = false;
    importConfigText.value = "";
    currentPreset.value = null;
    ElMessage.success("配置导入成功");
  } catch (error) {
    ElMessage.error("配置格式错误，请检查JSON格式");
  }
};

// 重置配置
const resetConfig = async () => {
  try {
    await ElMessageBox.confirm(
      "确定要重置到默认配置吗？这将清除所有自定义设置。",
      "重置确认",
      {
        confirmButtonText: "确定重置",
        cancelButtonText: "取消",
        type: "warning",
      },
    );

    FeatureManager.reset();
    emit("update");
    currentPreset.value = null;
    ElMessage.success("已重置为默认配置");
  } catch {
    // 用户取消
  }
};

// 监听特性变化，检测是否匹配预设配置
watch(
  () => props.features,
  (newFeatures) => {
    for (const [preset, config] of Object.entries(presetConfigs)) {
      const matches = Object.entries(config).every(([key, value]) => {
        return newFeatures[key as keyof FeatureFlags] === value;
      });
      if (matches) {
        currentPreset.value = preset;
        return;
      }
    }
    currentPreset.value = null;
  },
  { deep: true },
);
</script>

<style scoped>
.feature-panel {
  font-family:
    -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
}

.preset-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feature-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.feature-info {
  flex: 1;
}

.feature-name {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
  margin-bottom: 2px;
}

.feature-desc {
  font-size: 12px;
  color: #64748b;
}

.config-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.current-config {
  padding: 8px;
  background: #f1f5f9;
  border-radius: 4px;
  text-align: center;
}

:deep(.el-card) {
  border: 1px solid #e2e8f0;
}

:deep(.el-card__header) {
  padding: 12px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

:deep(.el-card__body) {
  padding: 16px;
}
</style>
