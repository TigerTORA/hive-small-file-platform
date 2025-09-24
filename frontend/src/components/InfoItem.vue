<template>
  <div class="info-item" :class="[`info-item--${layout}`]">
    <div class="info-item__label">
      <el-icon v-if="icon" class="info-item__label-icon">
        <component :is="icon" />
      </el-icon>
      <span>{{ label }}</span>
    </div>
    <div class="info-item__value">
      <slot name="value">
        <el-tooltip v-if="tooltip" :content="tooltip" placement="top">
          <span class="info-item__text" :class="{ 'info-item__text--highlight': highlight }">
            {{ displayValue }}
          </span>
        </el-tooltip>
        <span v-else class="info-item__text" :class="{ 'info-item__text--highlight': highlight }">
          {{ displayValue }}
        </span>
      </slot>
      <el-button
        v-if="copyable && resolvedCopyText"
        link
        size="small"
        class="info-item__copy"
        @click="handleCopy"
      >
        <el-icon><DocumentCopy /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'

interface Props {
  label: string
  value?: string | number | boolean | null
  fallback?: string
  icon?: string
  tooltip?: string
  copyable?: boolean
  copyText?: string
  layout?: 'horizontal' | 'vertical'
  highlight?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  value: null,
  fallback: '--',
  icon: '',
  tooltip: '',
  copyable: false,
  copyText: '',
  layout: 'vertical',
  highlight: false
})

const resolvedValue = computed(() => {
  if (props.value === null || props.value === undefined || props.value === '') {
    return ''
  }
  if (typeof props.value === 'boolean') {
    return props.value ? '是' : '否'
  }
  return String(props.value)
})

const displayValue = computed(() => resolvedValue.value || props.fallback)
const resolvedCopyText = computed(() => props.copyText || resolvedValue.value)

const handleCopy = async () => {
  if (!resolvedCopyText.value) {
    ElMessage.warning('暂无可复制内容')
    return
  }
  try {
    await navigator.clipboard.writeText(resolvedCopyText.value)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    try {
      const input = document.createElement('textarea')
      input.value = resolvedCopyText.value
      input.setAttribute('readonly', '')
      input.style.position = 'absolute'
      input.style.opacity = '0'
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
      ElMessage.success('已复制到剪贴板')
    } catch (fallbackError) {
      console.error('Copy failed', fallbackError)
      ElMessage.error('复制失败，请手动复制')
    }
  }
}
</script>

<style scoped>
.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  border-radius: 8px;
  border-bottom: 1px dashed #ebeef5;
  background: transparent;
  width: 100%;
  box-sizing: border-box;
}

.info-item--horizontal {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.info-item--horizontal .info-item__label {
  margin-bottom: 0;
  font-weight: 500;
}

.info-item--horizontal .info-item__value {
  justify-content: flex-end;
}

.info-item__label {
  font-size: 12px;
  font-weight: 500;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 4px;
}

.info-item__value {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 18px;
}

.info-item__text {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  word-break: break-all;
}

.info-item__text--highlight {
  color: var(--el-color-primary);
}

.info-item__copy {
  padding: 0;
  height: auto;
  min-height: 0;
}
.info-item:last-child {
  border-bottom: none;
}

</style>
