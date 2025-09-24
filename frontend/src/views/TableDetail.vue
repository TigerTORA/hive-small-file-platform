<template>
  <div class="table-detail">
    <div class="breadcrumb-container">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/dashboard' }">监控仪表板</el-breadcrumb-item>
        <el-breadcrumb-item :to="{ path: '/tables' }">表管理</el-breadcrumb-item>
        <el-breadcrumb-item>{{ clusterId }}.{{ database }}.{{ tableName }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div v-if="loading" class="loading-state">
      <el-card shadow="never">
        <div class="loading-container">
          <el-skeleton :rows="10" animated />
        </div>
      </el-card>
    </div>

    <template v-else-if="tableMetric">
      <div class="table-detail__layout">
        <el-card class="table-summary-card" shadow="hover">
          <div class="table-summary-card__header">
            <div>
              <div class="table-summary-card__title">{{ tableQualifiedName }}</div>
              <div class="table-summary-card__subtitle">
                最近扫描：{{ summaryMeta.lastScanText }}
                <span v-if="summaryMeta.lastScanFromNow">（{{ summaryMeta.lastScanFromNow }}）</span>
              </div>
              <div class="table-summary-card__tags">
                <el-tag :type="tableTypeTag.type">{{ tableTypeTag.label }}</el-tag>
                <el-tag v-if="storageFormatTag" type="info">{{ storageFormatTag }}</el-tag>
                <el-tag :type="tableMetric.is_partitioned ? 'success' : 'warning'" size="small">
                  {{ tableMetric.is_partitioned ? '分区表' : '非分区表' }}
                </el-tag>
              </div>
            </div>
            <div class="table-summary-card__actions">
              <el-button type="primary" :loading="scanningTableStrict" @click="scanCurrentTable(true)">
                <el-icon><RefreshRight /></el-icon>
                单表扫描
              </el-button>
              <template v-if="mergeSupported">
                <el-tooltip
                  v-if="tableMetric.small_files === 0"
                  content="暂无小文件，无需治理"
                  placement="top"
                >
                  <span>
                    <el-button type="success" :disabled="tableMetric.small_files === 0" @click="openMergeDialog">
                      <el-icon><Operation /></el-icon>
                      发起治理
                    </el-button>
                  </span>
                </el-tooltip>
                <el-button v-else type="success" @click="openMergeDialog">
                  <el-icon><Operation /></el-icon>
                  发起治理
                </el-button>
              </template>
              <el-tooltip v-else :content="unsupportedReason || '该表类型不支持合并'" placement="top">
                <span>
                  <el-button type="success" disabled>
                    <el-icon><Operation /></el-icon>
                    发起治理
                  </el-button>
                </span>
              </el-tooltip>
            </div>
          </div>

          <div class="table-summary-card__metrics">
            <div
              v-for="stat in summaryStats"
              :key="stat.label"
              class="summary-metric"
            >
              <div class="summary-metric__icon" :class="`summary-metric__icon--${stat.color}`">
                <el-icon><component :is="stat.icon" /></el-icon>
              </div>
              <div class="summary-metric__content">
                <div class="summary-metric__label">{{ stat.label }}</div>
                <div class="summary-metric__value">{{ stat.value }}</div>
                <div v-if="stat.description" class="summary-metric__desc">{{ stat.description }}</div>
              </div>
            </div>
          </div>
        </el-card>

        <div class="table-detail__grid">
          <el-card class="detail-card detail-card--span-6" shadow="never">
            <div class="table-detail__section-title">
              <el-icon><Collection /></el-icon>
              <span>基础信息</span>
            </div>
            <div class="info-grid info-grid--dense info-grid--inline">
              <InfoItem label="数据库" :value="tableMetric.database_name" icon="Collection" />
              <InfoItem label="表类型" :value="tableTypeTag.label" icon="Tickets" />
              <InfoItem label="所有者" :value="tableInfoSource.table_owner" icon="User" />
              <InfoItem label="创建时间" :value="formatTime(tableInfoSource.table_create_time)" icon="Timer" />
              <InfoItem label="归档状态" :value="archiveStatusLabel" icon="FolderChecked" :highlight="isArchived" />
              <InfoItem label="最后访问" :value="lastAccessLabel" icon="Clock" />
              <InfoItem label="数据活跃度" :value="coldDataLabel" icon="Histogram" />
            </div>
          </el-card>

          <el-card class="detail-card detail-card--span-6" shadow="never">
            <div class="table-detail__section-title">
              <el-icon><FolderOpened /></el-icon>
              <span>存储信息</span>
            </div>
            <div class="info-grid info-grid--inline">
              <InfoItem
                label="表路径"
                :value="tableLocationDisplay"
                icon="Folder"
                layout="vertical"
                :tooltip="tableLocationDisplay"
                :copyable="!!tableLocationRaw"
                :copy-text="tableLocationRaw"
              />
              <InfoItem
                label="存储格式"
                :value="storageFormatTag || 'UNKNOWN'"
                icon="CollectionTag"
              />
              <InfoItem
                label="压缩方式"
                :value="compressionLabel"
                icon="DataAnalysis"
              />
              <InfoItem
                label="InputFormat"
                :value="tableInfoSource.input_format"
                icon="ArrowDownBold"
                layout="vertical"
                :tooltip="tableInfoSource.input_format"
              />
              <InfoItem
                label="OutputFormat"
                :value="tableInfoSource.output_format"
                icon="ArrowUpBold"
                layout="vertical"
                :tooltip="tableInfoSource.output_format"
              />
              <InfoItem
                label="SerDe"
                :value="tableInfoSource.serde_lib"
                icon="MagicStick"
                layout="vertical"
                :tooltip="tableInfoSource.serde_lib"
              />
              <InfoItem
                label="分区字段"
                :value="partitionColumnsLabel"
                icon="Grid"
                layout="vertical"
                :tooltip="partitionColumnsLabel"
              />
            </div>
          </el-card>

          <el-card
            v-if="tableMetric.is_partitioned"
            class="detail-card detail-card--span-12 partition-table"
            shadow="never"
          >
            <div class="table-detail__section-title">
              <el-icon><Grid /></el-icon>
              <span>分区详情</span>
            </div>
            <div class="partition-table__meta">
              <span>共 {{ partitionTotal }} 个分区</span>
              <div class="partition-table__controls">
                <el-button size="small" :loading="partitionLoading" @click="refreshPartitionMetrics">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
                <span>并发度</span>
                <el-input-number
                  v-model="partitionConcurrency"
                  :min="1"
                  :max="20"
                  :step="1"
                  size="small"
                  @change="loadPartitionMetrics"
                />
              </div>
            </div>

            <div v-if="partitionLoading" class="loading-container">
              <el-skeleton :rows="5" animated />
            </div>
            <template v-else>
              <el-alert
                v-if="partitionError"
                :title="partitionError"
                type="error"
                :closable="false"
                style="margin-bottom: 12px"
              />

              <div v-if="partitionItems.length === 0" class="partition-table__empty">
                <el-empty description="暂无分区统计数据" />
              </div>
              <div v-else>
                <el-table :data="partitionItems" size="small" border>
                  <el-table-column prop="partition_spec" label="分区" min-width="220" />
                  <el-table-column prop="partition_path" label="路径" min-width="260">
                    <template #default="scope">
                      <el-tooltip :content="scope.row.partition_path" placement="top">
                        <span class="mono-text">{{ scope.row.partition_path || '--' }}</span>
                      </el-tooltip>
                    </template>
                  </el-table-column>
                  <el-table-column prop="file_count" label="文件数" width="100" />
                  <el-table-column prop="small_file_count" label="小文件数" width="120">
                    <template #default="scope">
                      <span :style="{ color: scope.row.small_file_count > 0 ? '#F56C6C' : '#67C23A' }">
                        {{ scope.row.small_file_count }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column label="小文件占比" width="160">
                    <template #default="scope">
                      <div class="ratio-bar">
                        <div class="ratio-bar__track">
                          <div
                            class="ratio-bar__fill"
                            :style="{
                              width: calcPartitionSmallRatio(scope.row) + '%',
                              background: getProgressColor(calcPartitionSmallRatio(scope.row))
                            }"
                          ></div>
                        </div>
                        <span class="ratio-bar__label">{{ calcPartitionSmallRatio(scope.row) }}%</span>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="平均文件大小" width="140">
                    <template #default="scope">
                      {{ formatFileSize(scope.row.avg_file_size || 0) }}
                    </template>
                  </el-table-column>
                  <el-table-column label="总大小" width="140">
                    <template #default="scope">
                      {{ formatFileSize(scope.row.total_size || 0) }}
                    </template>
                  </el-table-column>
                </el-table>
                <div class="partition-table__pagination">
                  <el-pagination
                    background
                    layout="prev, pager, next, sizes, total"
                    :total="partitionTotal"
                    :current-page="partitionPage"
                    :page-size="partitionPageSize"
                    :page-sizes="[50, 100, 200]"
                    @size-change="handlePartitionSizeChange"
                    @current-change="handlePartitionPageChange"
                  />
                </div>
              </div>
            </template>
          </el-card>

          <el-card class="detail-card detail-card--span-12" shadow="never">
            <div class="table-detail__section-title">
              <el-icon><Lightning /></el-icon>
              <span>智能优化建议</span>
            </div>
            <div class="recommendation-list">
              <div
                v-for="item in recommendationList"
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
                      @click="copyPlainText(item.copyText)"
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
              <div v-if="isTableHealthy" class="success-card">
                <el-icon class="success-card__icon"><CircleCheckFilled /></el-icon>
                当前表结构健康，无小文件风险。建议保持定期扫描与治理策略。
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </template>

    <div v-else class="no-data">
      <el-empty description="未找到表信息" />
    </div>

    <el-dialog
      v-model="showMergeDialog"
      title="数据治理"
      width="900px"
      class="governance-dialog"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template #header>
        <div class="dialog-header">
          <div class="dialog-header__icon">
            <el-icon><Operation /></el-icon>
          </div>
          <div class="dialog-header__content">
            <h3 class="dialog-header__title">数据治理</h3>
            <p class="dialog-header__subtitle">{{ tableQualifiedName }} - 统一治理配置</p>
          </div>
        </div>
      </template>

      <div class="governance-form-container">
        <el-form
          :model="mergeForm"
          :rules="mergeRules"
          ref="mergeFormRef"
          label-width="130px"
          class="governance-form"
        >
          <!-- 基础配置区域 -->
          <div class="form-section">
            <div class="form-section__header">
              <el-icon class="form-section__icon"><Setting /></el-icon>
              <h4 class="form-section__title">基础配置</h4>
            </div>
            <div class="form-section__content">
              <el-form-item label="任务名称" prop="task_name">
                <el-input
                  v-model="mergeForm.task_name"
                  placeholder="自动生成任务名称"
                  :prefix-icon="Edit"
                />
              </el-form-item>
              <template v-if="tableMetric?.is_partitioned">
                <el-form-item label="合并范围">
                  <el-radio-group v-model="mergeScope" class="scope-radio-group">
                    <el-radio label="table" class="scope-radio">
                      <div class="radio-option">
                        <el-icon><CollectionTag /></el-icon>
                        <span>整表</span>
                      </div>
                    </el-radio>
                    <el-radio label="partition" class="scope-radio">
                      <div class="radio-option">
                        <el-icon><Grid /></el-icon>
                        <span>指定分区</span>
                      </div>
                    </el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="选择分区" v-if="mergeScope === 'partition'">
                  <el-select
                    v-model="selectedPartition"
                    placeholder="选择一个分区"
                    filterable
                    style="width: 100%"
                    :prefix-icon="FolderOpened"
                  >
                    <el-option
                      v-for="p in partitionOptions"
                      :key="p"
                      :label="p"
                      :value="p"
                    />
                  </el-select>
                </el-form-item>
              </template>
              <el-form-item label="目标文件大小">
                <el-input-number
                  v-model="mergeForm.target_file_size"
                  :min="1024 * 1024"
                  :step="64 * 1024 * 1024"
                  placeholder="字节"
                  style="width: 200px"
                />
                <span class="form-hint-inline">字节（可选，建议 64MB-256MB）</span>
              </el-form-item>
            </div>
          </div>

          <!-- 格式优化区域 -->
          <div class="form-section">
            <div class="form-section__header">
              <el-icon class="form-section__icon"><DataAnalysis /></el-icon>
              <h4 class="form-section__title">格式优化</h4>
              <span class="form-section__badge">可选</span>
            </div>
            <div class="form-section__content">
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="存储格式">
                    <el-select
                      v-model="mergeForm.target_storage_format"
                      placeholder="保持原格式"
                      style="width: 100%"
                      clearable
                      :prefix-icon="CollectionTag"
                    >
                      <el-option label="ORC" value="ORC">
                        <div class="option-with-desc">
                          <span class="option-name">ORC</span>
                          <span class="option-desc">列式存储，高压缩比</span>
                        </div>
                      </el-option>
                      <el-option label="PARQUET" value="PARQUET">
                        <div class="option-with-desc">
                          <span class="option-name">PARQUET</span>
                          <span class="option-desc">跨平台列式格式</span>
                        </div>
                      </el-option>
                      <el-option label="TEXTFILE" value="TEXTFILE">
                        <div class="option-with-desc">
                          <span class="option-name">TEXTFILE</span>
                          <span class="option-desc">文本格式，兼容性好</span>
                        </div>
                      </el-option>
                      <el-option label="SEQUENCEFILE" value="SEQUENCEFILE">
                        <div class="option-with-desc">
                          <span class="option-name">SEQUENCEFILE</span>
                          <span class="option-desc">二进制格式</span>
                        </div>
                      </el-option>
                      <el-option label="AVRO" value="AVRO">
                        <div class="option-with-desc">
                          <span class="option-name">AVRO</span>
                          <span class="option-desc">模式演进支持</span>
                        </div>
                      </el-option>
                    </el-select>
                    <div class="form-hint">💾 建议使用 ORC 或 PARQUET 获得最佳性能</div>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="压缩格式">
                    <el-select
                      v-model="mergeForm.target_compression"
                      style="width: 100%"
                      :prefix-icon="DataAnalysis"
                    >
                      <el-option label="保持原样" value="KEEP">
                        <div class="option-with-desc">
                          <span class="option-name">保持原样</span>
                          <span class="option-desc">不改变压缩方式</span>
                        </div>
                      </el-option>
                      <el-option label="GZIP" value="GZIP">
                        <div class="option-with-desc">
                          <span class="option-name">GZIP</span>
                          <span class="option-desc">通用压缩，兼容性好</span>
                        </div>
                      </el-option>
                      <el-option label="SNAPPY" value="SNAPPY">
                        <div class="option-with-desc">
                          <span class="option-name">SNAPPY</span>
                          <span class="option-desc">快速压缩，推荐</span>
                        </div>
                      </el-option>
                      <el-option label="LZ4" value="LZ4">
                        <div class="option-with-desc">
                          <span class="option-name">LZ4</span>
                          <span class="option-desc">极速压缩</span>
                        </div>
                      </el-option>
                      <el-option label="ZSTD" value="ZSTD">
                        <div class="option-with-desc">
                          <span class="option-name">ZSTD</span>
                          <span class="option-desc">高压缩比</span>
                        </div>
                      </el-option>
                      <el-option label="BZIP2" value="BZIP2">
                        <div class="option-with-desc">
                          <span class="option-name">BZIP2</span>
                          <span class="option-desc">高压缩比，慢速</span>
                        </div>
                      </el-option>
                      <el-option label="无压缩" value="NONE">
                        <div class="option-with-desc">
                          <span class="option-name">无压缩</span>
                          <span class="option-desc">原始数据</span>
                        </div>
                      </el-option>
                    </el-select>
                    <div class="form-hint">🗜️ SNAPPY 提供速度与压缩比的最佳平衡</div>
                  </el-form-item>
                </el-col>
              </el-row>
            </div>
          </div>

          <!-- 存储策略区域 -->
          <div class="form-section">
            <div class="form-section__header">
              <el-icon class="form-section__icon"><Files /></el-icon>
              <h4 class="form-section__title">存储策略</h4>
              <span class="form-section__badge advanced">高级</span>
            </div>
            <div class="form-section__content">
              <!-- 存储策略 -->
              <div class="governance-item">
                <div class="governance-item__header">
                  <el-switch
                    v-model="mergeForm.storagePolicy"
                    size="large"
                    active-color="#13ce66"
                    inactive-color="#dcdfe6"
                  />
                  <div class="governance-item__title">
                    <el-icon><Folder /></el-icon>
                    <span>存储策略设置</span>
                  </div>
                </div>
                <transition name="fade-slide">
                  <div v-if="mergeForm.storagePolicy" class="governance-item__content">
                    <el-row :gutter="16" align="middle">
                      <el-col :span="8">
                        <el-select v-model="mergeForm.policy" style="width: 100%" placeholder="选择存储策略">
                          <el-option label="🧊 COLD - 冷存储" value="COLD" />
                          <el-option label="🔥 HOT - 热存储" value="HOT" />
                          <el-option label="🌡️ WARM - 温存储" value="WARM" />
                        </el-select>
                      </el-col>
                      <el-col :span="8">
                        <el-checkbox v-model="mergeForm.recursive" class="custom-checkbox">
                          <el-icon><FolderOpened /></el-icon>
                          递归应用
                        </el-checkbox>
                      </el-col>
                      <el-col :span="8">
                        <el-checkbox v-model="mergeForm.runMover" class="custom-checkbox">
                          <el-icon><Promotion /></el-icon>
                          执行 mover
                        </el-checkbox>
                      </el-col>
                    </el-row>
                    <div class="form-hint">💡 存储策略影响数据在集群中的物理分布和访问性能</div>
                  </div>
                </transition>
              </div>

              <!-- 纠删码 -->
              <div class="governance-item">
                <div class="governance-item__header">
                  <el-switch
                    v-model="mergeForm.ec"
                    size="large"
                    active-color="#13ce66"
                    inactive-color="#dcdfe6"
                  />
                  <div class="governance-item__title">
                    <el-icon><Grid /></el-icon>
                    <span>纠删码 (EC)</span>
                  </div>
                </div>
                <transition name="fade-slide">
                  <div v-if="mergeForm.ec" class="governance-item__content">
                    <el-row :gutter="16" align="middle">
                      <el-col :span="12">
                        <el-input
                          v-model="mergeForm.ecPolicy"
                          placeholder="RS-6-3-1024k"
                          style="width: 100%"
                          :prefix-icon="Setting"
                        >
                          <template #prepend>EC 策略</template>
                        </el-input>
                      </el-col>
                      <el-col :span="12">
                        <el-checkbox v-model="mergeForm.ecRecursive" class="custom-checkbox">
                          <el-icon><FolderOpened /></el-icon>
                          递归应用
                        </el-checkbox>
                      </el-col>
                    </el-row>
                    <div class="form-hint">🔧 通过 WebHDFS 执行 EC 策略设置，提高存储效率</div>
                  </div>
                </transition>
              </div>

              <!-- 副本策略 -->
              <div class="governance-item">
                <div class="governance-item__header">
                  <el-switch
                    v-model="mergeForm.setReplication"
                    size="large"
                    active-color="#13ce66"
                    inactive-color="#dcdfe6"
                  />
                  <div class="governance-item__title">
                    <el-icon><CopyDocument /></el-icon>
                    <span>副本策略</span>
                  </div>
                </div>
                <transition name="fade-slide">
                  <div v-if="mergeForm.setReplication" class="governance-item__content">
                    <el-row :gutter="16" align="middle">
                      <el-col :span="8">
                        <el-input-number
                          v-model="mergeForm.replicationFactor"
                          :min="1"
                          :max="6"
                          :step="1"
                          style="width: 100%"
                        />
                        <div class="form-hint" style="margin-top: 4px;">副本数量</div>
                      </el-col>
                      <el-col :span="16">
                        <el-checkbox v-model="mergeForm.replicationRecursive" class="custom-checkbox">
                          <el-icon><FolderOpened /></el-icon>
                          递归应用到子目录
                        </el-checkbox>
                      </el-col>
                    </el-row>
                    <div class="form-hint">📋 设置数据副本数量，影响可靠性和存储成本</div>
                  </div>
                </transition>
              </div>
            </div>
          </div>
        </el-form>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <div class="footer-info">
            <el-icon><InfoFilled /></el-icon>
            <span>治理任务将在后台执行，可在任务管理中查看进度</span>
          </div>
          <div class="footer-actions">
            <el-button @click="showMergeDialog = false" size="large">
              <el-icon><Close /></el-icon>
              取消
            </el-button>
            <el-button
              type="primary"
              @click="createMergeTask"
              :loading="creating"
              :disabled="mergeScope === 'partition' && !selectedPartition"
              size="large"
            >
              <el-icon v-if="!creating"><Check /></el-icon>
              <span>{{ creating ? '正在创建...' : '创建并执行' }}</span>
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <TaskRunDialog
      v-model="showRunDialog"
      :type="'archive'"
      :scan-task-id="runScanTaskId || undefined"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Operation, RefreshRight, Collection, Tickets, User, Timer, FolderChecked, Clock, Histogram,
  FolderOpened, CollectionTag, DataAnalysis, ArrowDownBold, ArrowUpBold, MagicStick, Grid,
  Refresh, DocumentCopy, CircleCheckFilled, Lightning, WarningFilled, Warning, InfoFilled,
  SetUp, PieChart, DocumentDelete, Lock, Connection, Edit, Setting, Files, Folder, Promotion,
  CopyDocument, Close, Check
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

import TaskRunDialog from '@/components/TaskRunDialog.vue'
import InfoItem from '@/components/InfoItem.vue'
import { tablesApi, type TableMetric } from '@/api/tables'
import { tasksApi, type MergeTaskCreate } from '@/api/tasks'
import { storageApi } from '@/api/storage'
import { formatFileSize } from '@/utils/formatFileSize'

dayjs.extend(relativeTime)

const route = useRoute()
const router = useRouter()

const clusterId = computed(() => Number(route.params.clusterId))
const database = computed(() => String(route.params.database))
const tableName = computed(() => String(route.params.tableName))

const loading = ref(true)
const creating = ref(false)
const scanningTableStrict = ref(false)

const showMergeDialog = ref(false)
const tableMetric = ref<TableMetric | null>(null)
const tableInfoExtra = ref<any | null>(null)
const mergeSupported = ref(true)
const unsupportedReason = ref('')

const partitionLoading = ref(false)
const partitionError = ref('')
const partitionItems = ref<any[]>([])
const partitionTotal = ref(0)
const partitionPage = ref(1)
const partitionPageSize = ref(50)
const partitionConcurrency = ref(5)

const mergeForm = ref<MergeTaskCreate & {
  storagePolicy?: boolean
  policy?: string
  recursive?: boolean
  runMover?: boolean
  ec?: boolean
  ecPolicy?: string
  ecRecursive?: boolean
  setReplication?: boolean
  replicationFactor?: number
  replicationRecursive?: boolean
}>({
  cluster_id: 0,
  task_name: '',
  table_name: '',
  database_name: '',
  partition_filter: '',
  merge_strategy: 'safe_merge',
  target_storage_format: null,
  target_compression: 'KEEP',
  use_ec: false,
  // 新增治理选项
  storagePolicy: false,
  policy: 'COLD',
  recursive: true,
  runMover: false,
  ec: false,
  ecPolicy: 'RS-6-3-1024k',
  ecRecursive: true,
  setReplication: false,
  replicationFactor: 3,
  replicationRecursive: false
})

const mergeScope = ref<'table' | 'partition'>('table')
const selectedPartition = ref('')
const partitionOptions = ref<string[]>([])

const mergeRules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }]
}

const mergeFormRef = ref()

const showRunDialog = ref(false)
const runScanTaskId = ref<string | null>(null)
const isArchived = computed(() => (tableMetric.value?.archive_status || '').toLowerCase() === 'archived')


const tableQualifiedName = computed(() => `${database.value}.${tableName.value}`)

const tableInfoSource = computed(() => ({
  ...(tableMetric.value || {}),
  ...(tableInfoExtra.value || {})
}))

const storageFormatTag = computed(() => {
  const format = (tableInfoSource.value.storage_format || '').toString().toUpperCase()
  return format || ''
})

const compressionLabel = computed(() => {
  const raw = (tableInfoSource.value.current_compression || '').toString().toUpperCase()
  if (!raw || raw === 'DEFAULT') return '默认'
  return raw
})

const tableTypeTag = computed(() => {
  const raw = (tableInfoSource.value.table_type || '').toString().toUpperCase()
  switch (raw) {
    case 'MANAGED_TABLE':
      return { label: '托管表', type: 'success' as const }
    case 'EXTERNAL_TABLE':
      return { label: '外部表', type: 'warning' as const }
    case 'VIEW':
      return { label: '视图', type: 'info' as const }
    default:
      return { label: raw || '未知', type: 'info' as const }
  }
})

const tableLocationRaw = computed(() => (tableInfoSource.value.table_path || '').toString())
const tableLocationDisplay = computed(() => tableLocationRaw.value || '--')

const partitionColumnsLabel = computed(() => {
  const raw = tableInfoSource.value.partition_columns
  if (!raw) return '--'
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (Array.isArray(parsed)) {
      return parsed.join(', ')
    }
  } catch (error) {
    return String(raw)
  }
  return String(raw)
})

const archiveStatusLabel = computed(() => {
  const label = (tableInfoSource.value.archive_status || '').toString()
  if (!label) return '未归档'
  return label.toUpperCase()
})

const lastAccessLabel = computed(() => {
  const access = tableInfoSource.value.last_access_time
  if (!access) return '--'
  return `${formatTime(access)}（${dayjs(access).fromNow()}）`
})

const coldDataLabel = computed(() => {
  if (!tableMetric.value) return '--'
  if (tableMetric.value.is_cold_data) {
    const days = tableMetric.value.days_since_last_access ?? 0
    return `冷数据（${days} 天未访问）`
  }
  return '活跃'
})

const smallFileRatio = computed(() => {
  if (!tableMetric.value || !tableMetric.value.total_files) return 0
  return Math.round((tableMetric.value.small_files / tableMetric.value.total_files) * 100)
})

const progressColor = computed(() => getProgressColor(smallFileRatio.value))

const summaryMeta = computed(() => {
  const scanTime = tableMetric.value?.scan_time
  if (!scanTime) {
    return { lastScanText: '--', lastScanFromNow: '' }
  }
  const formatted = formatTime(scanTime)
  const relative = dayjs(scanTime).isValid() ? dayjs(scanTime).fromNow() : ''
  return { lastScanText: formatted, lastScanFromNow: relative }
})

const summaryStats = computed(() => {
  if (!tableMetric.value) return []
  const ratio = smallFileRatio.value
  const files = tableMetric.value.total_files
  const smallFiles = tableMetric.value.small_files

  const severity = ratio >= 80 ? 'danger' : ratio >= 50 ? 'warning' : ratio > 0 ? 'primary' : 'success'

  const totalSize = typeof tableMetric.value.total_size === 'number' ? tableMetric.value.total_size : null
  const avgSize = typeof tableMetric.value.avg_file_size === 'number' ? tableMetric.value.avg_file_size : null
  const totalSizeLabel = totalSize !== null ? formatFileSize(totalSize) : '--'
  const avgSizeLabel = avgSize !== null ? formatFileSize(avgSize) : '--'

  const stats = [
    {
      label: '小文件占比',
      value: `${ratio}%`,
      icon: 'PieChart',
      color: severity,
      description: files ? `小文件 ${formatNumber(smallFiles)} / 总数 ${formatNumber(files)}` : '暂无文件'
    },
    {
      label: '小文件数',
      value: formatNumber(smallFiles),
      icon: 'DocumentDelete',
      color: severity,
      description: `总文件数 ${formatNumber(files)}`
    },
    {
      label: '表数据量',
      value: totalSizeLabel,
      icon: 'DataAnalysis',
      color: 'primary',
      description: `平均大小 ${avgSizeLabel}`
    }
  ]

  if (tableMetric.value.is_partitioned) {
    const partitionCount = tableMetric.value.partition_count || 0
    const avgPerPartition = partitionCount
      ? Math.max(1, Math.round(tableMetric.value.total_files / partitionCount))
      : 0
    stats.push({
      label: '分区数量',
      value: formatNumber(partitionCount),
      icon: 'Grid',
      color: 'info',
      description: partitionCount ? `平均 ${formatNumber(avgPerPartition)} 文件/分区` : '暂无分区数据'
    })
  }

  return stats
})

interface RecommendationItem {
  id: string
  icon: string
  severity: 'danger' | 'warning' | 'info' | 'success'
  title: string
  summary: string
  tips?: string[]
  copyText?: string
}

const recommendationList = computed<RecommendationItem[]>(() => {
  if (!tableMetric.value) return []

  const items: RecommendationItem[] = []
  const ratio = smallFileRatio.value

  if (tableMetric.value.small_files > 0) {
    const severity = ratio >= 80 ? 'danger' : ratio >= 50 ? 'warning' : 'info'
    const tips = getSmallFileSuggestions()
    const summary = getSmallFileImpact()
    const title = `小文件问题：${formatNumber(tableMetric.value.small_files)} 个（${ratio}%）`
    items.push({
      id: 'small-files',
      icon: severity === 'danger' ? 'WarningFilled' : severity === 'warning' ? 'Warning' : 'InfoFilled',
      severity,
      title,
      summary,
      tips,
      copyText: [title, summary, ...tips].join('\n')
    })
  }

  const storageAdvice = getStorageFormatAdvice()
  if (storageAdvice) {
    items.push({
      id: 'storage',
      icon: 'SetUp',
      severity: 'info',
      title: '存储格式优化',
      summary: storageAdvice,
      copyText: storageAdvice
    })
  }

  const partitionAdvice = getPartitionAdvice()
  if (partitionAdvice) {
    items.push({
      id: 'partition',
      icon: 'Grid',
      severity: 'info',
      title: '分区策略优化',
      summary: partitionAdvice,
      copyText: partitionAdvice
    })
  }

  return items
})

const isTableHealthy = computed(() => !!tableMetric.value && tableMetric.value.small_files === 0)

const loadTableInfo = async (options: { skipLoading?: boolean } = {}) => {
  if (!options.skipLoading) {
    loading.value = true
  }
  try {
    const metrics = await tablesApi.getMetrics(clusterId.value, database.value)
    tableMetric.value =
      metrics.find(
        (metric: TableMetric) =>
          metric.database_name === database.value && metric.table_name === tableName.value
      ) || null

    if (tableMetric.value) {
      mergeForm.value = {
        cluster_id: clusterId.value,
        task_name: `merge_${database.value}_${tableName.value}_${Date.now()}`,
        table_name: tableName.value,
        database_name: database.value,
        partition_filter: '',
        merge_strategy: 'safe_merge',
        target_storage_format: null,
        target_compression: 'KEEP',
        use_ec: false
      }

      if (tableMetric.value.is_partitioned) {
        try {
          const resp = await tasksApi.getTablePartitions(
            clusterId.value,
            database.value,
            tableName.value
          )
          const parts = (resp?.partitions || resp || []) as string[]
          partitionOptions.value = parts
        } catch (error) {
          partitionOptions.value = []
        }
      } else {
        mergeScope.value = 'table'
        partitionOptions.value = []
        partitionItems.value = []
        partitionTotal.value = 0
      }

      try {
        const info = await tasksApi.getTableInfo(clusterId.value, database.value, tableName.value)
        if (info && Object.prototype.hasOwnProperty.call(info, 'merge_supported')) {
          mergeSupported.value = info.merge_supported !== false
        } else {
          mergeSupported.value = true
        }
        unsupportedReason.value =
          info?.unsupported_reason && info.merge_supported === false
            ? info.unsupported_reason
            : ''
        tableInfoExtra.value = info || null
      } catch (error) {
        mergeSupported.value = true
        unsupportedReason.value = ''
        tableInfoExtra.value = null
      }

      if (tableMetric.value.is_partitioned) {
        await loadPartitionMetrics()
      }
    } else {
      partitionItems.value = []
      partitionTotal.value = 0
    }
  } catch (error) {
    console.error('Failed to load table info:', error)
    ElMessage.error('加载表信息失败')
  } finally {
    if (!options.skipLoading) {
      loading.value = false
    }
  }
}


const getHarSshDefaults = () => {
  try {
    const raw = localStorage.getItem(`har-ssh.${clusterId.value}`)
    return raw ? JSON.parse(raw) : null
  } catch (error) {
    return null
  }
}



const loadPartitionMetrics = async () => {
  if (!tableMetric.value?.is_partitioned) return
  partitionLoading.value = true
  partitionError.value = ''
  try {
    const { items, total } = await tablesApi.getPartitionMetrics(
      clusterId.value,
      database.value,
      tableName.value,
      partitionPage.value,
      partitionPageSize.value,
      partitionConcurrency.value
    )
    partitionItems.value = items || []
    partitionTotal.value = total || 0
  } catch (error: any) {
    console.error('Failed to load partition metrics:', error)
    partitionError.value = error?.message || '加载分区统计失败'
  } finally {
    partitionLoading.value = false
  }
}

const refreshPartitionMetrics = async () => {
  await loadPartitionMetrics()
}

const handlePartitionSizeChange = async (size: number) => {
  partitionPageSize.value = size
  partitionPage.value = 1
  await loadPartitionMetrics()
}

const handlePartitionPageChange = async (page: number) => {
  partitionPage.value = page
  await loadPartitionMetrics()
}

const calcPartitionSmallRatio = (row: any): number => {
  const files = Number(row?.file_count || 0)
  const small = Number(row?.small_file_count || 0)
  if (!files) return 0
  return Math.round((small / files) * 100)
}

const createMergeTask = async () => {
  try {
    await mergeFormRef.value?.validate()
    creating.value = true
    if (tableMetric.value?.is_partitioned && mergeScope.value === 'partition') {
      if (!selectedPartition.value) {
        ElMessage.warning('请选择分区')
        creating.value = false
        return
      }
      mergeForm.value.partition_filter = specToFilter(selectedPartition.value)
    } else {
      mergeForm.value.partition_filter = ''
    }

    // 始终使用安全合并策略
    mergeForm.value.merge_strategy = 'safe_merge'

    const payload = { ...mergeForm.value }
    if (mergeScope.value === 'partition') {
      payload.use_ec = false
    }
    if (!payload.target_storage_format) {
      delete payload.target_storage_format
    } else {
      payload.target_storage_format = payload.target_storage_format.toUpperCase() as MergeTaskCreate['target_storage_format']
    }
    if (payload.target_compression) {
      payload.target_compression = payload.target_compression.toUpperCase() as MergeTaskCreate['target_compression']
    }

    const task = await tasksApi.create(payload)
    await tasksApi.execute(task.id)

    // 处理附加的治理选项
    const additionalTasks: string[] = []
    const path = tableLocationRaw.value
    const cid = clusterId.value

    // 存储策略设置
    if (mergeForm.value.storagePolicy) {
      const resp = await tablesApi.archiveTableWithProgress(cid, database.value, tableName.value, false, {
        mode: 'storage-policy',
        policy: mergeForm.value.policy!,
        recursive: mergeForm.value.recursive!
      })
      if ((resp as any)?.task_id) additionalTasks.push((resp as any).task_id)
    }

    // 副本策略设置
    if (mergeForm.value.setReplication) {
      const targetRep = Math.max(1, Number(mergeForm.value.replicationFactor || 1))
      const repResp = await storageApi.setReplication(cid, {
        path,
        replication: targetRep,
        recursive: mergeForm.value.replicationRecursive!
      })
      if ((repResp as any)?.task_id) additionalTasks.push((repResp as any).task_id)
    }

    // 纠删码设置
    if (mergeForm.value.ec) {
      const ssh = getHarSshDefaults()
      if (!ssh || !ssh.host) {
        ElMessage.warning('请先在集群管理维护 SSH 配置')
      } else {
        const ecResp = await storageApi.setEcPolicy(cid, {
          path,
          policy: mergeForm.value.ecPolicy || 'RS-6-3-1024k',
          recursive: mergeForm.value.ecRecursive!,
          ssh_host: ssh.host,
          ssh_user: ssh.user || 'hdfs',
          ssh_port: ssh.port || 22,
          ssh_key_path: ssh.keyPath,
          kinit_principal: ssh.principal,
          kinit_keytab: ssh.keytab
        })
        if ((ecResp as any)?.task_id) additionalTasks.push((ecResp as any).task_id)
      }
    }

    // Mover执行
    if (mergeForm.value.runMover) {
      const ssh = getHarSshDefaults()
      if (!ssh || !ssh.host) {
        ElMessage.warning('请先在集群管理维护 SSH 配置')
      } else {
        const mover = await storageApi.runMover(cid, {
          path,
          ssh_host: ssh.host,
          ssh_user: ssh.user || 'hdfs',
          ssh_port: ssh.port || 22,
          ssh_key_path: ssh.keyPath,
          kinit_principal: ssh.principal,
          kinit_keytab: ssh.keytab
        })
        if ((mover as any)?.task_id) additionalTasks.push((mover as any).task_id)
      }
    }

    ElMessage.success(`治理任务已创建并启动${additionalTasks.length > 0 ? `，包含 ${additionalTasks.length + 1} 个子任务` : ''}`)
    showMergeDialog.value = false

    // 如果有附加任务，显示任务执行对话框
    if (additionalTasks.length > 0) {
      runScanTaskId.value = additionalTasks[additionalTasks.length - 1]
      showRunDialog.value = true
    } else {
      router.push('/tasks')
    }
  } catch (error) {
    console.error('Failed to create merge task:', error)
    ElMessage.error('创建合并任务失败')
  } finally {
    creating.value = false
  }
}

const openMergeDialog = async () => {
  if (tableMetric.value?.is_partitioned && partitionOptions.value.length === 0) {
    try {
      const resp = await tasksApi.getTablePartitions(
        clusterId.value,
        database.value,
        tableName.value
      )
      const parts = (resp?.partitions || resp || []) as string[]
      partitionOptions.value = parts
    } catch (error) {
      partitionOptions.value = []
    }
  }
  mergeScope.value = tableMetric.value?.is_partitioned ? 'partition' : 'table'
  selectedPartition.value = ''
  mergeForm.value.target_storage_format = null
  mergeForm.value.target_compression = 'KEEP'
  mergeForm.value.cluster_id = clusterId.value
  mergeForm.value.use_ec = false
  // 初始化新的治理选项
  mergeForm.value.storagePolicy = false
  mergeForm.value.policy = 'COLD'
  mergeForm.value.recursive = true
  mergeForm.value.runMover = false
  mergeForm.value.ec = false
  mergeForm.value.ecPolicy = 'RS-6-3-1024k'
  mergeForm.value.ecRecursive = true
  mergeForm.value.setReplication = false
  mergeForm.value.replicationFactor = 3
  mergeForm.value.replicationRecursive = false
  showMergeDialog.value = true
}

const scanCurrentTable = async (strictReal: boolean) => {
  if (!tableMetric.value || scanningTableStrict.value) return
  scanningTableStrict.value = true
  try {
    await tablesApi.scanTable(clusterId.value, database.value, tableName.value, strictReal)
    ElMessage.success('已启动单表扫描')
    setTimeout(() => {
      loadTableInfo({ skipLoading: true })
    }, 1500)
  } catch (error: any) {
    console.error('scanCurrentTable failed', error)
    const msg = error?.response?.data?.detail || error?.message || '启动单表扫描失败'
    ElMessage.error(msg)
  } finally {
    scanningTableStrict.value = false
  }
}

const specToFilter = (spec: string): string => {
  const parts = String(spec || '').split('/')
  const filters = parts
    .map(p => {
      const [k, v] = p.split('=')
      if (!k || v === undefined) return ''
      const quoted = /^\d+$/.test(v) ? v : `'${v}'`
      return `${k}=${quoted}`
    })
    .filter(Boolean)
  return filters.join(' AND ')
}

const formatTime = (time?: string): string => {
  if (!time) return '--'
  return dayjs(time).isValid() ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '--'
}

const formatScanDuration = (seconds?: number): string => {
  if (!seconds || Number.isNaN(seconds)) return '--'
  if (seconds < 60) return `${Math.round(seconds)} 秒`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return secs ? `${mins} 分 ${secs} 秒` : `${mins} 分`
}

const getProgressColor = (percentage: number): string => {
  if (percentage > 80) return '#f56c6c'
  if (percentage > 50) return '#e6a23c'
  if (percentage > 20) return '#1989fa'
  return '#67c23a'
}

const numberFormatter = new Intl.NumberFormat('zh-CN', {
  maximumFractionDigits: 2
})

const formatNumber = (num: number | null | undefined): string => {
  if (num === null || num === undefined || Number.isNaN(num)) return '--'
  return numberFormatter.format(num)
}

const getSmallFileRatio = (): number => {
  if (!tableMetric.value || tableMetric.value.total_files === 0) return 0
  return Math.round((tableMetric.value.small_files / tableMetric.value.total_files) * 100)
}

const getSmallFileImpact = (): string => {
  const ratio = getSmallFileRatio()
  if (ratio >= 80) return '严重影响查询性能，强烈建议立即进行文件合并优化'
  if (ratio >= 50) return '显著影响查询效率，建议尽快进行文件合并优化'
  if (ratio >= 20) return '轻微影响查询性能，建议安排文件合并任务'
  return '小文件数量较少，但仍建议定期进行文件整理'
}

const getSmallFileSuggestions = (): string[] => {
  if (!tableMetric.value) return []
  const suggestions: string[] = []
  const ratio = getSmallFileRatio()

  if (ratio >= 80) {
    suggestions.push('立即执行安全合并策略，可显著降低查询开销')
    suggestions.push('检查写入链路，避免产生更多小文件')
  } else if (ratio >= 50) {
    suggestions.push('使用安全合并策略进行文件合并')
    suggestions.push('建议在业务低峰期执行合并任务')
  } else {
    suggestions.push('可择机进行文件合并优化')
    suggestions.push('监控后续写入，防止小文件累积')
  }

  if (tableMetric.value.is_partitioned) {
    suggestions.push('分区表可按分区逐步合并，降低对业务的影响')
  }

  if ((tableMetric.value.storage_format || '').toUpperCase() === 'TEXT') {
    suggestions.push('考虑转换为 ORC / Parquet 等列式格式以提升性能')
  }

  return suggestions
}

const getStorageFormatAdvice = (): string | null => {
  if (!tableMetric.value) return null

  const format = (tableMetric.value.storage_format || '').toUpperCase()
  const totalSize = tableMetric.value.total_size

  if (format === 'TEXT') {
    if (totalSize > 100 * 1024 * 1024) {
      return '当前使用 TEXT 格式，建议转换为 ORC 或 Parquet，预计可减少存储开销并显著提升查询性能'
    }
    return 'TEXT 格式不支持列式优化，仍建议评估升级为 ORC 或 Parquet'
  }

  if (format === 'SEQUENCE' || format === 'AVRO') {
    return `${format} 格式功能完整但性能逊于列式存储，建议评估转换到 ORC/Parquet 的可行性`
  }

  if (format === 'ORC' || format === 'PARQUET') {
    return null
  }

  return `建议评估当前 ${format || '未知'} 格式是否最佳，可对比 ORC/Parquet 的压缩与查询表现`
}

const getPartitionAdvice = (): string | null => {
  if (!tableMetric.value) return null

  const { is_partitioned, partition_count, total_files, total_size } = tableMetric.value

  if (!is_partitioned) {
    if (total_size > 1024 * 1024 * 1024) {
      return '大表建议引入分区策略（按日期/业务字段），可显著提升查询性能'
    }
    return null
  }

  if (partition_count > 10000) {
    return `分区数量过多（${partition_count} 个），可能造成元数据压力，建议合并小分区或调整策略`
  }

  if (partition_count > 0 && total_files / partition_count < 5) {
    return '平均每个分区文件数过少，建议合并小分区或调整写入批次'
  }

  return null
}

const copyPlainText = async (value?: string) => {
  if (!value) {
    ElMessage.warning('暂无可复制内容')
    return
  }
  try {
    await navigator.clipboard.writeText(value)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    try {
      const input = document.createElement('textarea')
      input.value = value
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

watch(
  () => mergeScope.value,
  scope => {
    if (scope === 'partition') {
      mergeForm.value.use_ec = false
    }
  }
)

onMounted(() => {
  loadTableInfo()
})
</script>

<style scoped>
.table-detail__grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 6px;
  align-items: stretch;
  grid-auto-flow: row dense;
}

.table-detail {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.table-detail .breadcrumb-container {
  margin-bottom: 8px;
}

.table-detail__layout {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.table-summary-card {
  position: relative;
  padding-bottom: 4px;
  width: 100%;
  box-sizing: border-box;
}

.table-summary-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
}

.table-summary-card__title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2d3d;
  margin-bottom: 2px;
}

.table-summary-card__subtitle {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.table-summary-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.table-summary-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 2px 0;
  position: sticky;
  top: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), #ffffff);
  border-radius: 10px;
  z-index: 2;
}

.table-summary-card__metrics {
  margin-top: 8px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.summary-metric {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f5f7fa;
}

.summary-metric__icon {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
}

.summary-metric__icon--primary {
  background: var(--el-color-primary);
}

.summary-metric__icon--warning {
  background: var(--el-color-warning);
}

.summary-metric__icon--danger {
  background: var(--el-color-danger);
}

.summary-metric__icon--success {
  background: var(--el-color-success);
}

.summary-metric__content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-metric__label {
  font-size: 10px;
  color: #909399;
}

.summary-metric__value {
  font-size: 14px;
  font-weight: 600;
  color: #1f2d3d;
}

.summary-metric__desc {
  font-size: 9px;
  color: #909399;
}

.detail-card--span-6 {
  grid-column: span 6;
}

.detail-card--span-12 {
  grid-column: span 12;
}

@media (max-width: 1280px) {
  .detail-card--span-6 {
    grid-column: span 12;
  }
}


.table-detail__section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2d3d;
  margin-bottom: 10px;
}

.detail-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
}

.detail-card {
  min-height: 140px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px;
  align-items: stretch;
}

.info-grid--dense {
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  align-items: stretch;
}

.info-grid--inline {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 6px;
}

.info-grid--inline :deep(.info-item) {
  width: 100%;
  min-width: 0;
  border-bottom: none;
  padding: 6px 10px;
  background: transparent;
}

@media (max-width: 1280px) {
  .info-grid--inline {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }
}

.partition-table__meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.partition-table__controls {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 12px;
}

.partition-table__pagination {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.ratio-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.ratio-bar__track {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: #ebeef5;
  overflow: hidden;
}

.ratio-bar__fill {
  height: 100%;
  border-radius: 999px;
  background: var(--el-color-primary);
  transition: width 0.3s ease;
}

.ratio-bar__label {
  font-size: 12px;
  color: #606266;
  min-width: 48px;
  text-align: right;
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

.recommendation-list__icon--danger {
  background: var(--el-color-danger);
}

.recommendation-list__icon--warning {
  background: var(--el-color-warning);
}

.recommendation-list__icon--info {
  background: var(--el-color-primary);
}

.recommendation-list__icon--success {
  background: var(--el-color-success);
}

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

.loading-state {
  margin-bottom: 12px;
}

.loading-container {
  padding: 16px;
}

.no-data {
  padding: 24px;
  text-align: center;
}

.form-hint {
  margin-top: 6px;
  font-size: 10px;
  color: #909399;
}

.form-hint-inline {
  margin-left: 8px;
  font-size: 11px;
  color: #909399;
}

.form-spacer {
  margin-top: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
}

.footer-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 12px;
  flex: 1;
}

.footer-actions {
  display: flex;
  gap: 12px;
}

/* 治理对话框样式 */
.governance-dialog {
  --dialog-border-radius: 16px;
}

.governance-dialog :deep(.el-dialog) {
  border-radius: var(--dialog-border-radius);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.1);
}

.governance-dialog :deep(.el-dialog__header) {
  padding: 0;
  border-bottom: 1px solid #f0f0f0;
}

.governance-dialog :deep(.el-dialog__body) {
  padding: 16px;
  max-height: 70vh;
  overflow-y: auto;
}

.governance-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
}

.dialog-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: var(--dialog-border-radius) var(--dialog-border-radius) 0 0;
}

.dialog-header__icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.dialog-header__title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.dialog-header__subtitle {
  font-size: 14px;
  opacity: 0.9;
  margin: 4px 0 0 0;
}

.governance-form-container {
  background: #fafbfc;
  border-radius: 12px;
  margin: -8px;
  padding: 8px;
}

.governance-form {
  background: white;
  border-radius: 8px;
  padding: 16px;
}

/* 表单区域样式 */
.form-section {
  margin-bottom: 16px;
  border: 1px solid #e8eaec;
  border-radius: 12px;
  overflow: hidden;
  background: white;
  transition: all 0.3s ease;
}

.form-section:hover {
  border-color: #c0c4cc;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.form-section__header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(90deg, #f8f9fa 0%, #ffffff 100%);
  border-bottom: 1px solid #e8eaec;
}

.form-section__icon {
  color: #409eff;
  font-size: 18px;
}

.form-section__title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2d3d;
  margin: 0;
  flex: 1;
}

.form-section__badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 500;
  background: #e1f3d8;
  color: #529b2e;
}

.form-section__badge.advanced {
  background: #fdf6ec;
  color: #e6a23c;
}

.form-section__content {
  padding: 16px;
}

/* 治理项样式 */
.governance-item {
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fafbfc;
  transition: all 0.3s ease;
}

.governance-item:hover {
  border-color: #409eff;
  background: #f0f9ff;
}

.governance-item__header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  cursor: pointer;
}

.governance-item__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 500;
  color: #1f2d3d;
  flex: 1;
}

.governance-item__content {
  padding: 0 16px 16px 16px;
  border-top: 1px solid #ebeef5;
  background: white;
}

/* 单选按钮增强样式 */
.scope-radio-group {
  display: flex;
  gap: 16px;
}

.scope-radio {
  flex: 1;
}

.scope-radio :deep(.el-radio__input) {
  display: none;
}

.scope-radio :deep(.el-radio__label) {
  padding: 0;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
}

.scope-radio.is-checked .radio-option {
  border-color: #409eff;
  background: #ecf5ff;
  color: #409eff;
}



/* 选项描述样式 */
.option-with-desc {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.option-name {
  font-weight: 500;
  color: #1f2d3d;
}

.option-desc {
  font-size: 11px;
  color: #909399;
}

/* 自定义复选框 */
.custom-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 6px;
  background: #f5f7fa;
  transition: all 0.3s ease;
}

.custom-checkbox:hover {
  background: #eef1f6;
}

.custom-checkbox.is-checked {
  background: #e1f3d8;
  color: #529b2e;
}

/* 过渡动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.fade-slide-enter-from {
  opacity: 0;
  max-height: 0;
  transform: translateY(-10px);
}

.fade-slide-leave-to {
  opacity: 0;
  max-height: 0;
  transform: translateY(-10px);
}

.fade-slide-enter-to,
.fade-slide-leave-from {
  opacity: 1;
  max-height: 200px;
  transform: translateY(0);
}

/* 响应式优化 */
@media (max-width: 768px) {
  .governance-dialog :deep(.el-dialog) {
    width: 95% !important;
    margin: 20px auto;
  }

  .governance-dialog :deep(.el-dialog__body) {
    padding: 16px;
    max-height: 60vh;
  }

  .dialog-header {
    padding: 20px;
    flex-direction: column;
    text-align: center;
    gap: 12px;
  }

  .dialog-footer {
    flex-direction: column;
    gap: 12px;
  }

  .footer-info {
    text-align: center;
  }

  .footer-actions {
    width: 100%;
    justify-content: center;
  }


  .form-section__content {
    padding: 16px;
  }

  .governance-item__content {
    padding: 0 16px 16px 16px;
  }
}

.mono-text {
  font-family: 'SFMono-Regular', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  display: inline-block;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

:deep(.el-card__body) {
  padding: 12px;
}

:deep(.detail-card .el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
}

.detail-card {
  width: 100%;
  box-sizing: border-box;
}

:deep(.partition-table .el-table__header-wrapper) {
  position: sticky;
  top: 0;
  z-index: 1;
}

@media (max-width: 768px) {
  .table-summary-card__header {
    flex-direction: column;
  }

  .table-summary-card__actions {
    position: static;
    background: transparent;
    width: 100%;
  }
}
</style>
