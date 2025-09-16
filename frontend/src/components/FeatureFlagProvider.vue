<template>
  <div>
    <slot :features="features" :isEnabled="isEnabled" />

    <!-- 开发环境下的特性开关面板 -->
    <FeatureFlagPanel
      v-if="showPanel && isDevelopment"
      v-model:visible="panelVisible"
      :features="features"
      @update="handleFeatureUpdate"
    />

    <!-- 浮动按钮（开发模式） -->
    <el-button
      v-if="isDevelopment"
      type="primary"
      circle
      :icon="Setting"
      class="feature-toggle-btn"
      @click="panelVisible = true"
      title="特性开关"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, provide } from 'vue'
import { Setting } from '@element-plus/icons-vue'
import { FeatureManager, type FeatureFlags } from '@/utils/feature-flags'
import FeatureFlagPanel from './FeatureFlagPanel.vue'

interface Props {
  showPanel?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showPanel: true
})

const panelVisible = ref(false)
const features = ref<FeatureFlags>(FeatureManager.getAllFeatures())

const isDevelopment = computed(() => import.meta.env.DEV)

// 检查特性是否启用
const isEnabled = (feature: keyof FeatureFlags): boolean => {
  return FeatureManager.isEnabled(feature)
}

// 处理特性更新
const handleFeatureUpdate = () => {
  features.value = FeatureManager.getAllFeatures()
}

// 提供给子组件使用
provide('featureFlags', {
  features: computed(() => features.value),
  isEnabled,
  enable: FeatureManager.enable,
  disable: FeatureManager.disable,
  toggle: FeatureManager.toggle,
})

// URL参数检测
onMounted(() => {
  const urlParams = new URLSearchParams(window.location.search)

  // 检查演示模式
  if (urlParams.get('demo') === 'true') {
    FeatureManager.enable('demoMode')
    FeatureManager.enable('advancedCharts')
    FeatureManager.enable('smartRecommendations')
  }

  // 检查全屏模式
  if (urlParams.get('fullscreen') === 'true') {
    FeatureManager.enable('fullscreenMode')
  }

  // 检查深色主题
  if (urlParams.get('theme') === 'dark') {
    FeatureManager.enable('darkTheme')
  }

  // 刷新特性状态
  features.value = FeatureManager.getAllFeatures()
})
</script>

<style scoped>
.feature-toggle-btn {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 2000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}
</style>