<template>
  <el-card class="detail-card detail-card--span-12" shadow="never">
    <div class="section-title">
      <el-icon><Lightning /></el-icon>
      <span>智能优化建议</span>
    </div>
    <div class="recommendation-list">
      <div
        v-for="item in recommendations"
        :key="item.id"
        class="recommendation-list__item"
      >
        <div class="recommendation-list__icon" :class="`recommendation-list__icon--${item.severity}`">
          <el-icon><component :is="item.icon" /></el-icon>
        </div>
        <div class="recommendation-list__content">
          <div class="recommendation-list__title">
            {{ item.title }}
            <el-button
              v-if="item.copyText"
              link
              type="primary"
              size="small"
              @click="handleCopy(item.copyText)"
            >
              <el-icon><DocumentCopy /></el-icon>
              复制建议
            </el-button>
          </div>
          <p class="recommendation-list__desc">{{ item.summary }}</p>
          <ul v-if="item.tips?.length">
            <li v-for="tip in item.tips" :key="tip">{{ tip }}</li>
          </ul>
        </div>
      </div>
      <div v-if="isHealthy" class="success-card">
        <el-icon class="success-card__icon"><CircleCheckFilled /></el-icon>
        当前表结构健康，无小文件风险。建议保持定期扫描与治理策略。
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { Lightning, DocumentCopy, CircleCheckFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { copyPlainText } from '@/utils/tableHelpers'
import type { RecommendationItem } from '@/composables/useTableMetrics'

interface Props {
  recommendations: RecommendationItem[]
  isHealthy: boolean
}

defineProps<Props>()

const handleCopy = async (text: string) => {
  const success = await copyPlainText(text)
  if (success) {
    ElMessage.success('已复制到剪贴板')
  } else {
    ElMessage.error('复制失败，请手动复制')
  }
}
</script>

<style scoped>
.detail-card--span-12 {
  grid-column: span 12;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2d3d;
  margin-bottom: 10px;
}

.recommendation-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recommendation-list__item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px;
  border-radius: 10px;
  background: #f8f9fb;
}

.recommendation-list__icon {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.recommendation-list__icon--danger { background: var(--el-color-danger); }
.recommendation-list__icon--warning { background: var(--el-color-warning); }
.recommendation-list__icon--info { background: var(--el-color-primary); }
.recommendation-list__icon--success { background: var(--el-color-success); }

.recommendation-list__content {
  flex: 1;
}

.recommendation-list__title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2d3d;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.recommendation-list__desc {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  margin: 0 0 6px;
}

.recommendation-list__content ul {
  margin: 0 0 0 20px;
  padding: 0;
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
}

.recommendation-list__content li {
  margin-bottom: 4px;
}

.success-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  background: #e8f7ee;
  color: #1f2d3d;
  font-size: 12px;
}

.success-card__icon {
  color: var(--el-color-success);
  font-size: 18px;
}
</style>
