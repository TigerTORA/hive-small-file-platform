<template>
  <div class="draggable-grid-container">
    <!-- 布局控制栏 -->
    <div class="layout-controls" v-if="showControls">
      <div class="controls-left">
        <el-text class="controls-title">
          <el-icon><Grid /></el-icon>
          自定义布局
        </el-text>
        <el-text type="info" size="small" class="controls-desc">
          {{
            isEditMode
              ? "拖拽卡片重新排列，调整大小"
              : "点击编辑按钮开始自定义布局"
          }}
        </el-text>
      </div>

      <div class="controls-right">
        <el-button-group>
          <el-button
            :type="isEditMode ? 'warning' : 'primary'"
            @click="toggleEditMode"
            :icon="isEditMode ? Lock : Edit"
            size="small"
          >
            {{ isEditMode ? "锁定布局" : "编辑布局" }}
          </el-button>

          <el-button
            @click="resetLayout"
            :icon="RefreshLeft"
            size="small"
            :disabled="!canReset"
          >
            重置布局
          </el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 可拖拽网格布局 -->
    <grid-layout
      :layout="currentLayout"
      :col-num="colNum"
      :row-height="rowHeight"
      :is-draggable="isDraggable"
      :is-resizable="isResizable"
      :is-mirrored="false"
      :vertical-compact="true"
      :margin="[16, 16]"
      :use-css-transforms="true"
      :responsive="true"
      :breakpoints="breakpoints"
      :cols="responsiveCols"
      @layout-updated="handleLayoutUpdate"
      @layout-ready="handleLayoutReady"
      class="grid-layout-container"
    >
      <grid-item
        v-for="item in currentLayout"
        :key="item.i"
        :x="item.x"
        :y="item.y"
        :w="item.w"
        :h="item.h"
        :i="item.i"
        :static="item.static || !isEditMode"
        :drag-allow-from="isEditMode ? '.drag-handle' : null"
        :resize-ignore-from="isEditMode ? '.no-resize' : '.grid-item-content'"
        class="grid-item-wrapper"
        :class="{
          'edit-mode': isEditMode,
          'locked-mode': !isEditMode,
        }"
      >
        <!-- 编辑模式的拖拽手柄 -->
        <div v-if="isEditMode" class="drag-handle">
          <el-icon><Rank /></el-icon>
          <span class="drag-hint">{{ getCardTitle(item.i) }}</span>
        </div>

        <!-- 卡片内容 -->
        <div class="grid-item-content" :class="{ 'has-handle': isEditMode }">
          <slot :name="item.i" :item="item" :edit-mode="isEditMode">
            <div class="placeholder-card">
              <el-icon size="32"><Document /></el-icon>
              <p>{{ getCardTitle(item.i) }}</p>
            </div>
          </slot>
        </div>

        <!-- 编辑模式的调整大小指示器 -->
        <div v-if="isEditMode" class="resize-indicator">
          <el-icon><BottomRight /></el-icon>
        </div>
      </grid-item>
    </grid-layout>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, defineEmits, defineProps } from "vue";
import { GridLayout, GridItem } from "vue3-grid-layout-next";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Grid,
  Edit,
  Lock,
  RefreshLeft,
  Rank,
  Document,
  BottomRight,
} from "@element-plus/icons-vue";

export interface GridItemLayout {
  i: string; // 唯一标识
  x: number; // X坐标（网格单位）
  y: number; // Y坐标（网格单位）
  w: number; // 宽度（网格单位）
  h: number; // 高度（网格单位）
  static?: boolean; // 是否静态（不可拖拽和调整）
  minW?: number; // 最小宽度
  minH?: number; // 最小高度
  maxW?: number; // 最大宽度
  maxH?: number; // 最大高度
}

export interface CardConfig {
  id: string;
  title: string;
  defaultLayout: Omit<GridItemLayout, "i">;
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
}

// Props
interface Props {
  cards: CardConfig[]; // 卡片配置
  initialLayout?: GridItemLayout[]; // 初始布局
  showControls?: boolean; // 是否显示控制栏
  colNum?: number; // 列数
  rowHeight?: number; // 行高
}

const props = withDefaults(defineProps<Props>(), {
  showControls: true,
  colNum: 12,
  rowHeight: 60,
  initialLayout: () => [],
});

// Emits
const emit = defineEmits<{
  layoutChange: [layout: GridItemLayout[]];
  editModeChange: [editMode: boolean];
  layoutReset: [];
}>();

// 响应式设置
const breakpoints = { lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 };
const responsiveCols = { lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 };

// 状态管理
const isEditMode = ref(false);
const currentLayout = ref<GridItemLayout[]>([]);
const originalLayout = ref<GridItemLayout[]>([]);

// 计算属性
const isDraggable = computed(() => isEditMode.value);
const isResizable = computed(() => isEditMode.value);
const canReset = computed(() => {
  return (
    JSON.stringify(currentLayout.value) !== JSON.stringify(originalLayout.value)
  );
});

// 工具函数
const getCardTitle = (cardId: string): string => {
  const card = props.cards.find((c) => c.id === cardId);
  return card?.title || cardId;
};

const generateDefaultLayout = (): GridItemLayout[] => {
  return props.cards.map((card) => ({
    i: card.id,
    ...card.defaultLayout,
    minW: card.minW,
    minH: card.minH,
    maxW: card.maxW,
    maxH: card.maxH,
  }));
};

// 事件处理
const toggleEditMode = () => {
  isEditMode.value = !isEditMode.value;
  emit("editModeChange", isEditMode.value);
};

const resetLayout = async () => {
  if (!canReset.value) return;

  try {
    await ElMessageBox.confirm("确定要重置布局到默认状态吗？", "重置布局", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });

    currentLayout.value = [...originalLayout.value];
    emit("layoutChange", currentLayout.value);
    emit("layoutReset");
    ElMessage.success("布局已重置");
  } catch {
    // 用户取消
  }
};

const handleLayoutUpdate = (newLayout: GridItemLayout[]) => {
  currentLayout.value = newLayout;
  emit("layoutChange", newLayout);
};

const handleLayoutReady = () => {
  console.log("Grid layout is ready");
};

// 初始化布局
const initializeLayout = () => {
  if (props.initialLayout.length > 0) {
    currentLayout.value = [...props.initialLayout];
  } else {
    currentLayout.value = generateDefaultLayout();
  }
  originalLayout.value = generateDefaultLayout();
};

// 监听 cards 变化
watch(
  () => props.cards,
  () => {
    initializeLayout();
  },
  { immediate: true, deep: true },
);

// 组件挂载
onMounted(() => {
  initializeLayout();
});
</script>

<style scoped>
.draggable-grid-container {
  width: 100%;
}

.layout-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  margin-bottom: 16px;
  border: 1px solid #e4e7ed;
}

.controls-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.controls-title {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.controls-desc {
  font-size: 12px;
  margin-left: 20px;
}

.controls-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.grid-layout-container {
  position: relative;
  background: transparent;
}

.grid-item-wrapper {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 2px solid transparent;
  overflow: hidden;
  transition: all 0.3s ease;
  position: relative;
}

.grid-item-wrapper:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

.grid-item-wrapper.edit-mode {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.2);
  transition: all 0.2s ease;
}

.grid-item-wrapper.edit-mode:hover {
  border-color: #79bbff;
  transform: none;
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.3);
}

.grid-item-wrapper.edit-mode .drag-handle:hover {
  background: linear-gradient(135deg, #337ecc, #6ba6ff);
  cursor: grab;
}

.grid-item-wrapper.edit-mode .drag-handle:active {
  cursor: grabbing;
}

.grid-item-wrapper.locked-mode {
  cursor: default;
}

.drag-handle {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 32px;
  background: linear-gradient(135deg, #409eff, #79bbff);
  color: white;
  display: flex;
  align-items: center;
  padding: 0 12px;
  cursor: move;
  z-index: 10;
  font-size: 12px;
  font-weight: 500;
}

.drag-hint {
  margin-left: 4px;
  opacity: 0.9;
}

.grid-item-content {
  height: 100%;
  width: 100%;
  position: relative;
  overflow: hidden;
}

.grid-item-content.has-handle {
  padding-top: 32px;
  height: calc(100% - 32px);
}

.resize-indicator {
  position: absolute;
  bottom: 4px;
  right: 4px;
  color: #909399;
  font-size: 12px;
  opacity: 0.6;
  pointer-events: none;
}

.placeholder-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #909399;
  background: #f9fafc;
}

.placeholder-card .el-icon {
  margin-bottom: 8px;
}

.placeholder-card p {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
}

/* 响应式适配 */
@media (max-width: 1200px) {
  .grid-layout-container {
    margin: 0 -8px;
  }

  .grid-item-wrapper {
    margin: 0 8px;
  }
}

@media (max-width: 996px) {
  .layout-controls {
    padding: 14px 20px;
    border-radius: 8px;
    margin-bottom: 12px;
  }

  .controls-title {
    font-size: 14px;
  }

  .controls-desc {
    font-size: 11px;
  }
}

@media (max-width: 768px) {
  .layout-controls {
    flex-direction: column;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 8px;
  }

  .controls-left {
    text-align: center;
  }

  .controls-desc {
    margin-left: 0;
    font-size: 11px;
  }

  .grid-item-wrapper {
    border-radius: 8px;
  }

  .drag-handle {
    height: 28px;
    font-size: 11px;
    padding: 0 8px;
  }

  .grid-item-content.has-handle {
    padding-top: 28px;
    height: calc(100% - 28px);
  }
}

@media (max-width: 480px) {
  .layout-controls {
    padding: 8px 12px;
    margin-bottom: 8px;
  }

  .controls-title {
    font-size: 13px;
  }

  .controls-desc {
    font-size: 10px;
  }

  .grid-item-wrapper {
    border-radius: 6px;
    box-shadow: 0 1px 8px rgba(0, 0, 0, 0.08);
  }

  .grid-item-wrapper:hover {
    transform: none;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
  }

  .drag-handle {
    height: 24px;
    font-size: 10px;
    padding: 0 6px;
  }

  .grid-item-content.has-handle {
    padding-top: 24px;
    height: calc(100% - 24px);
  }

  .resize-indicator {
    bottom: 2px;
    right: 2px;
    font-size: 10px;
  }
}

/* 拖拽时的样式 */
:deep(.vue-grid-item.vue-draggable-dragging) {
  opacity: 0.9;
  transform: rotate(1deg) scale(1.02);
  z-index: 999;
  transition: none;
  box-shadow: 0 8px 32px rgba(64, 158, 255, 0.4);
}

:deep(.vue-grid-item.vue-resizable-resizing) {
  opacity: 0.9;
  z-index: 999;
  transition: none;
  box-shadow: 0 4px 24px rgba(64, 158, 255, 0.3);
}

/* 占位符样式 */
:deep(.vue-grid-placeholder) {
  background: linear-gradient(
    45deg,
    rgba(64, 158, 255, 0.05),
    rgba(64, 158, 255, 0.15)
  );
  border: 2px dashed #409eff;
  border-radius: 12px;
  opacity: 0.9;
  animation: placeholder-pulse 1.5s ease-in-out infinite;
}

@keyframes placeholder-pulse {
  0%,
  100% {
    opacity: 0.6;
  }
  50% {
    opacity: 0.9;
  }
}
</style>
