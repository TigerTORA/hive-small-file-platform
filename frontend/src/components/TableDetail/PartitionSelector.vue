<template>
  <div class="partition-selector">
    <el-tabs :model-value="selectMode" @update:model-value="onModeChange">
      <el-tab-pane label="智能选择" name="smart">
        <div class="smart-selector">
          <div class="range-selector" style="margin-bottom: 16px;">
            <el-radio-group :model-value="rangeMode" @update:model-value="(val) => { emit('update:rangeMode', val); emit('time-range-mode-change'); }">
              <el-radio label="recent">最近</el-radio>
              <el-radio label="range">指定范围</el-radio>
              <el-radio label="pattern">模式匹配</el-radio>
            </el-radio-group>
          </div>

          <!-- 最近N天 -->
          <div v-if="rangeMode === 'recent'" class="recent-selector">
            <el-row :gutter="12" style="align-items: center;">
              <el-col :span="8">
                <el-input-number
                  :model-value="recentDays"
                  @update:model-value="emit('update:recentDays', $event)"
                  :min="1"
                  :max="365"
                  @change="emit('recent-days-change')"
                  style="width: 100%"
                />
              </el-col>
              <el-col :span="4">
                <span>天内的分区</span>
              </el-col>
              <el-col :span="12">
                <el-button size="small" @click="emit('select-recent')">
                  选择 (预计{{ predictedRecentCount }}个)
                </el-button>
              </el-col>
            </el-row>
          </div>

          <!-- 日期范围 -->
          <div v-if="rangeMode === 'range'" class="date-range-selector">
            <el-row :gutter="12">
              <el-col :span="10">
                <el-date-picker
                  :model-value="dateRange"
                  @update:model-value="emit('update:dateRange', $event)"
                  type="daterange"
                  range-separator="至"
                  start-placeholder="开始日期"
                  end-placeholder="结束日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                  @change="emit('date-range-change')"
                />
              </el-col>
              <el-col :span="6">
                <el-button size="small" @click="emit('select-date-range')">
                  选择 (预计{{ predictedRangeCount }}个)
                </el-button>
              </el-col>
              <el-col :span="8">
                <el-checkbox
                  :model-value="excludeWeekends"
                  @update:model-value="emit('update:excludeWeekends', $event)"
                >
                  排除周末
                </el-checkbox>
              </el-col>
            </el-row>
          </div>

          <!-- 模式匹配 -->
          <div v-if="rangeMode === 'pattern'" class="pattern-selector">
            <el-row :gutter="12">
              <el-col :span="12">
                <el-input
                  :model-value="partitionPattern"
                  @update:model-value="emit('update:partitionPattern', $event)"
                  placeholder="例如: dt=2025-09-*, dt=2025-09-2?, dt>=2025-09-01"
                  @input="emit('pattern-change')"
                >
                  <template #prepend>匹配模式</template>
                </el-input>
              </el-col>
              <el-col :span="6">
                <el-button size="small" @click="emit('select-pattern')">
                  选择 (预计{{ predictedPatternCount }}个)
                </el-button>
              </el-col>
              <el-col :span="6">
                <el-button size="small" @click="emit('preview-pattern')" type="info">预览</el-button>
              </el-col>
            </el-row>
            <div style="margin-top: 8px; font-size: 12px; color: #909399;">
              支持通配符: * (任意字符), ? (单个字符), >= <= (比较操作)
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="手动选择" name="manual">
        <div class="manual-selector">
          <!-- 搜索和过滤 -->
          <div class="search-bar" style="margin-bottom: 12px;">
            <el-row :gutter="12">
              <el-col :span="12">
                <el-input
                  :model-value="searchText"
                  @update:model-value="emit('update:searchText', $event)"
                  placeholder="搜索分区..."
                  clearable
                  @input="emit('partition-search')"
                >
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                </el-input>
              </el-col>
              <el-col :span="6">
                <el-button size="small" @click="emit('select-all-filtered')">
                  全选筛选结果 ({{ filteredCount }})
                </el-button>
              </el-col>
              <el-col :span="6">
                <el-button size="small" @click="emit('clear-selection')">
                  清空选择
                </el-button>
              </el-col>
            </el-row>
          </div>

          <!-- 分区列表 -->
          <div class="partition-list" style="height: 200px; border: 1px solid #e4e7ed; border-radius: 4px;">
            <el-checkbox-group
              :model-value="modelValue"
              @update:model-value="emit('update:modelValue', $event)"
              style="width: 100%;"
            >
              <el-scrollbar height="200px">
                <div style="padding: 8px;">
                  <el-checkbox
                    v-for="partition in paginatedPartitions"
                    :key="partition"
                    :label="partition"
                    :value="partition"
                    style="display: block; margin-bottom: 8px;"
                  >
                    {{ partition }}
                  </el-checkbox>
                  <div v-if="hasMore" style="text-align: center; padding: 8px;">
                    <el-button size="small" @click="emit('load-more')">
                      加载更多... (剩余{{ remaining }}个)
                    </el-button>
                  </div>
                </div>
              </el-scrollbar>
            </el-checkbox-group>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 选择结果摘要 -->
    <div class="selection-summary">
      <el-row :gutter="12" style="align-items: center;">
        <el-col :span="12">
          <span style="color: #606266; font-size: 14px;">
            已选择: <strong>{{ modelValue.length }}</strong> / {{ totalCount }} 个分区
          </span>
        </el-col>
        <el-col :span="12" style="text-align: right;">
          <el-button v-if="modelValue.length > 0" size="small" @click="emit('show-details')">
            查看选择详情
          </el-button>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Search } from '@element-plus/icons-vue'

interface Props {
  modelValue: string[]
  selectMode: 'smart' | 'manual'
  rangeMode: 'recent' | 'range' | 'pattern'
  recentDays: number
  predictedRecentCount: number
  dateRange: [string, string] | null
  excludeWeekends: boolean
  predictedRangeCount: number
  partitionPattern: string
  predictedPatternCount: number
  searchText: string
  filteredCount: number
  paginatedPartitions: string[]
  hasMore: boolean
  remaining: number
  totalCount: number
}

defineProps<Props>()

const emit = defineEmits([
  'update:modelValue',
  'update:selectMode',
  'update:rangeMode',
  'update:recentDays',
  'update:dateRange',
  'update:excludeWeekends',
  'update:partitionPattern',
  'update:searchText',
  'mode-change',
  'time-range-mode-change',
  'recent-days-change',
  'select-recent',
  'date-range-change',
  'select-date-range',
  'pattern-change',
  'select-pattern',
  'preview-pattern',
  'partition-search',
  'select-all-filtered',
  'clear-selection',
  'load-more',
  'show-details'
])

const onModeChange = (mode: 'smart' | 'manual') => {
  emit('update:selectMode', mode)
  emit('mode-change', mode)
}
</script>

<style scoped>
.partition-selector {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px;
  background-color: #fafafa;
}

.selection-summary {
  margin-top: 12px;
  padding: 8px;
  background-color: #f5f7fa;
  border-radius: 4px;
}
</style>
