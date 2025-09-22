<template>
  <div class="table-detail">
    <div class="breadcrumb-container">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/dashboard' }">监控仪表板</el-breadcrumb-item>
        <el-breadcrumb-item :to="{ path: '/tables' }">表管理</el-breadcrumb-item>
        <el-breadcrumb-item>{{ clusterId }}.{{ database }}.{{ tableName }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <el-card class="table-info-card">
      <template #header>
        <div class="card-header">
          <span>表详情</span>
          <div class="header-actions">
            <el-button
              type="primary"
              @click="refreshTableInfo"
              :loading="loading"
            >
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <template v-if="mergeSupported">
              <el-button
                type="success"
                @click="openMergeDialog"
                :disabled="!tableMetric || tableMetric.small_files === 0"
              >
                <el-icon><Operation /></el-icon>
                一键合并
              </el-button>
            </template>
            <template v-else>
              <el-tooltip
                :content="unsupportedReason || '该表类型不支持合并'"
                placement="top"
              >
                <span>
                  <el-button
                    type="success"
                    disabled
                  >
                    <el-icon><Operation /></el-icon>
                    一键合并
                  </el-button>
                </span>
              </el-tooltip>
            </template>
            <el-divider direction="vertical" />
            <el-button type="warning" :disabled="!tableMetric" @click="archiveTableBg('storage-policy')">存储策略归档（COLD）</el-button>
            <el-button
              type="success"
              @click="restoreTableBg"
              :disabled="!tableMetric || !isArchived"
            >
              恢复（后台）
            </el-button>
          </div>
        </div>
      </template>

      <div
        v-if="loading"
        class="loading-container"
      >
        <el-skeleton
          :rows="6"
          animated
        />
      </div>

      <div
        v-else-if="tableMetric"
        class="table-info-content"
      >
        <!-- 基本信息 -->
        <div class="info-section">
          <h3>基本信息</h3>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic
                title="表名"
                :value="tableMetric.table_name"
              />
            </el-col>
            <el-col :span="6">
              <el-statistic
                title="数据库"
                :value="tableMetric.database_name"
              />
            </el-col>
            <el-col :span="6">
              <div class="statistic-item">
                <div class="statistic-title">表类型</div>
                <el-tag
                  :type="getTableTypeColor(tableMetric.table_type)"
                  size="default"
                >
                  {{ formatTableType(tableMetric.table_type) }}
                </el-tag>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="statistic-item">
                <div class="statistic-title">存储格式</div>
                <el-tag
                  type="info"
                  size="default"
                >
                  {{ tableMetric.storage_format || 'UNKNOWN' }}
                </el-tag>
              </div>
            </el-col>
          </el-row>

          <el-row
            :gutter="20"
            style="margin-top: 16px"
          >
            <el-col :span="6">
              <div class="statistic-item">
                <div class="statistic-title">分区表</div>
                <el-tag
                  :type="tableMetric.is_partitioned ? 'success' : 'info'"
                  size="default"
                >
                  {{ tableMetric.is_partitioned ? '是' : '否' }}
                </el-tag>
              </div>
            </el-col>
            <el-col
              :span="6"
              v-if="tableMetric.is_partitioned"
            >
              <el-statistic
                title="分区数量"
                :value="tableMetric.partition_count"
              />
            </el-col>
            <el-col :span="6">
              <el-statistic
                title="表拥有者"
                :value="tableMetric.table_owner || 'Unknown'"
              />
            </el-col>
            <el-col
              :span="6"
              v-if="tableMetric.table_create_time"
            >
              <el-statistic
                title="创建时间"
                :value="formatTime(tableMetric.table_create_time)"
              />
            </el-col>
          </el-row>
        </div>

        <!-- 文件统计 -->
        <div class="info-section">
          <h3>文件统计</h3>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic
                title="总文件数"
                :value="tableMetric.total_files"
              />
            </el-col>
            <el-col :span="6">
              <el-statistic
                title="小文件数"
                :value="tableMetric.small_files"
                :value-style="{ color: tableMetric.small_files > 0 ? '#f56c6c' : '#67c23a' }"
              />
            </el-col>
            <el-col :span="6">
              <div class="statistic-item">
                <div class="statistic-title">小文件占比</div>
                <el-progress
                  :percentage="
                    Math.round((tableMetric.small_files / tableMetric.total_files) * 100)
                  "
                  :color="
                    getProgressColor((tableMetric.small_files / tableMetric.total_files) * 100)
                  "
                  :show-text="true"
                  style="width: 120px"
                />
              </div>
            </el-col>
            <el-col :span="6">
              <el-statistic
                title="总大小"
                :value="formatFileSize(tableMetric.total_size)"
              />
            </el-col>
          </el-row>
        </div>

        <!-- 扫描信息 -->
        <div class="info-section">
          <h3>扫描信息</h3>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-statistic
                title="最后扫描时间"
                :value="formatTime(tableMetric.scan_time)"
              />
            </el-col>
            <el-col :span="12">
              <div class="statistic-item">
                <div class="statistic-title">扫描状态</div>
                <el-tag
                  type="success"
                  size="default"
                  >已完成</el-tag
                >
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 分区小文件详情 -->
        <div
          class="info-section"
          v-if="tableMetric.is_partitioned"
        >
          <div class="partitions-header">
            <h3>分区小文件详情</h3>
            <div class="header-actions">
              <el-button
                size="small"
                @click="refreshPartitionMetrics"
                :loading="partitionLoading"
              >
                <el-icon><Refresh /></el-icon>
                刷新分区统计
              </el-button>
              <div class="concurrency-control">
                <span class="label">并发度</span>
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
          </div>

          <div
            v-if="partitionLoading"
            class="loading-container"
          >
            <el-skeleton
              :rows="5"
              animated
            />
          </div>

          <template v-else>
            <el-alert
              v-if="partitionError"
              :title="partitionError"
              type="error"
              :closable="false"
              style="margin-bottom: 12px"
            />

            <div class="partitions-summary">
              <span>共 {{ partitionTotal }} 个分区</span>
            </div>

            <el-table
              :data="partitionItems"
              stripe
              border
              size="small"
            >
              <el-table-column
                prop="partition_spec"
                label="分区"
                min-width="220"
              />
              <el-table-column
                prop="partition_path"
                label="路径"
                min-width="300"
                show-overflow-tooltip
              />
              <el-table-column
                prop="file_count"
                label="文件数"
                width="100"
              />
              <el-table-column
                prop="small_file_count"
                label="小文件数"
                width="110"
              >
                <template #default="scope">
                  <span :style="{ color: scope.row.small_file_count > 0 ? '#F56C6C' : '#67C23A' }">
                    {{ scope.row.small_file_count }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column
                label="小文件占比"
                width="120"
              >
                <template #default="scope">
                  <el-progress
                    :percentage="calcPartitionSmallRatio(scope.row)"
                    :color="getProgressColor(calcPartitionSmallRatio(scope.row))"
                    :show-text="true"
                  />
                </template>
              </el-table-column>
              <el-table-column
                label="平均文件大小"
                width="140"
              >
                <template #default="scope">{{
                  formatFileSize(scope.row.avg_file_size || 0)
                }}</template>
              </el-table-column>
              <el-table-column
                label="总大小"
                width="140"
              >
                <template #default="scope">{{
                  formatFileSize(scope.row.total_size || 0)
                }}</template>
              </el-table-column>
            </el-table>

            <div class="partitions-actions">
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
          </template>
        </div>

        <!-- 优化建议 -->
        <div class="info-section">
          <h3>智能优化建议</h3>
          <div class="recommendations">
            <!-- 小文件问题 -->
            <el-alert
              v-if="tableMetric.small_files > 0"
              :title="`🚨 小文件问题：检测到 ${tableMetric.small_files} 个小文件（${getSmallFileRatio()}%）`"
              :type="getSmallFileSeverity()"
              :closable="false"
              style="margin-bottom: 12px"
            >
              <template #default>
                <div class="recommendation-content">
                  <p><strong>影响分析：</strong>{{ getSmallFileImpact() }}</p>
                  <p><strong>推荐策略：</strong></p>
                  <ul>
                    <li
                      v-for="suggestion in getSmallFileSuggestions()"
                      :key="suggestion"
                    >
                      {{ suggestion }}
                    </li>
                  </ul>
                </div>
              </template>
            </el-alert>

            <!-- 存储格式建议 -->
            <el-alert
              v-if="getStorageFormatAdvice()"
              title="💾 存储格式优化"
              type="info"
              :closable="false"
              style="margin-bottom: 12px"
            >
              <template #default>
                <div class="recommendation-content">
                  <p>{{ getStorageFormatAdvice() }}</p>
                </div>
              </template>
            </el-alert>

            <!-- 分区优化建议 -->
            <el-alert
              v-if="getPartitionAdvice()"
              title="🗂️ 分区优化"
              type="info"
              :closable="false"
              style="margin-bottom: 12px"
            >
              <template #default>
                <div class="recommendation-content">
                  <p>{{ getPartitionAdvice() }}</p>
                </div>
              </template>
            </el-alert>

            <!-- 健康状态 -->
            <el-alert
              v-if="tableMetric.small_files === 0 && tableMetric.total_files > 0"
              title="✅ 表状态健康"
              type="success"
              :closable="false"
            >
              <template #default>
                <p>当前表文件结构良好，无小文件问题。继续保持良好的数据管理实践！</p>
              </template>
            </el-alert>
          </div>
        </div>
      </div>

      <div
        v-else
        class="no-data"
      >
        <el-empty description="未找到表信息" />
      </div>
    </el-card>

    <!-- 合并任务对话框 -->
    <el-dialog
      v-model="showMergeDialog"
      title="创建合并任务"
      width="520px"
    >
      <el-form
        :model="mergeForm"
        :rules="mergeRules"
        ref="mergeFormRef"
        label-width="120px"
      >
        <el-form-item
          label="任务名称"
          prop="task_name"
        >
          <el-input
            v-model="mergeForm.task_name"
            placeholder="自动生成任务名称"
          />
        </el-form-item>
        <template v-if="tableMetric?.is_partitioned">
          <el-form-item label="合并范围">
            <el-radio-group v-model="mergeScope">
              <el-radio label="table">整表</el-radio>
              <el-radio label="partition">指定分区</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item
            label="选择分区"
            v-if="mergeScope === 'partition'"
          >
            <el-select
              v-model="selectedPartition"
              placeholder="选择一个分区"
              filterable
              style="width: 100%"
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
        <el-form-item label="合并策略">
          <el-radio-group v-model="mergeForm.merge_strategy">
            <el-radio label="safe_merge">安全合并 (推荐)</el-radio>
            <el-radio label="concatenate">文件合并</el-radio>
            <el-radio label="insert_overwrite">重写插入</el-radio>
          </el-radio-group>
          <div style="margin-top: 4px; font-size: 12px; color: #909399">
            安全合并使用临时表+重命名策略，确保零停机时间
          </div>
        </el-form-item>
        <el-form-item label="目标文件大小">
          <el-input-number
            v-model="mergeForm.target_file_size"
            :min="1024 * 1024"
            :step="64 * 1024 * 1024"
            placeholder="字节"
          />
          <span style="margin-left: 8px; color: #909399">字节（可选）</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showMergeDialog = false">取消</el-button>
          <el-button
            type="primary"
            @click="createMergeTask"
            :loading="creating"
            :disabled="mergeScope === 'partition' && !selectedPartition"
            >创建并执行</el-button
          >
        </div>
      </template>
    </el-dialog>
  </div>
  <TaskRunDialog
    v-model="showRunDialog"
    :type="'archive'"
    :scan-task-id="runScanTaskId || undefined"
  />
  <el-dialog v-model="showPolicyDialog" title="归档策略" width="640px">
    <el-form label-width="140px">
      <el-form-item label="合并压缩">
        <el-switch v-model="policyForm.merge" />
        <template v-if="policyForm.merge">
          <div style="margin-top:8px"></div>
          <el-checkbox v-model="policyForm.mergeSingleFile">单文件</el-checkbox>
          <el-input-number v-model="policyForm.mergeTargetSizeMB" :min="16" :step="64" style="margin-left:12px" />
          <span style="margin-left:6px">MB/文件</span>
          <div style="font-size:12px;color:#909399;margin-top:6px">当前使用 INSERT OVERWRITE；“单文件/格式/Codec”将在引擎扩展后完全生效</div>
        </template>
      </el-form-item>
      <el-form-item label="存储策略">
        <el-switch v-model="policyForm.storagePolicy" />
        <template v-if="policyForm.storagePolicy">
          <div style="margin-top:8px"></div>
          <el-select v-model="policyForm.policy" style="width:160px">
            <el-option label="COLD" value="COLD" />
            <el-option label="HOT" value="HOT" />
            <el-option label="WARM" value="WARM" />
          </el-select>
          <el-checkbox v-model="policyForm.recursive" style="margin-left:12px">递归</el-checkbox>
          <el-checkbox v-model="policyForm.runMover" style="margin-left:12px">执行 mover</el-checkbox>
        </template>
      </el-form-item>
      <el-form-item label="纠删码(EC)">
        <el-switch v-model="policyForm.ec" />
        <template v-if="policyForm.ec">
          <div style="margin-top:8px"></div>
          <el-input v-model="policyForm.ecPolicy" placeholder="RS-6-3-1024k" style="width: 220px" />
          <el-checkbox v-model="policyForm.ecRecursive" style="margin-left:12px">递归</el-checkbox>
          <div style="font-size:12px;color:#909399;margin-top:6px">通过 SSH 执行 hdfs ec -setPolicy</div>
        </template>
      </el-form-item>
      <el-form-item label="HAR 归档">
        <el-switch v-model="policyForm.har" />
        <template v-if="policyForm.har">
          <div style="margin-top:8px"></div>
          <el-input v-model="policyForm.harArchiveName" placeholder="category.har" style="width: 220px" />
          <el-input v-model="policyForm.harDestDir" placeholder="/archive/har/default" style="width: 300px; margin-left:12px" />
          <div style="font-size:12px;color:#909399;margin-top:6px">SSH 参数从“集群管理→HAR SSH 配置”读取</div>
        </template>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showPolicyDialog=false">取消</el-button>
      <el-button type="primary" @click="runArchiveStrategy">开始</el-button>
    </template>
  </el-dialog>
  <el-dialog v-model="showPolicyDialog" title="归档策略" width="640px">
    <el-form label-width="140px">
      <el-form-item label="存储策略">
        <el-switch v-model="policyForm.storagePolicy" />
        <template v-if="policyForm.storagePolicy">
          <div style="margin-top:8px"></div>
          <el-select v-model="policyForm.policy" style="width:160px">
            <el-option label="COLD" value="COLD" />
            <el-option label="HOT" value="HOT" />
            <el-option label="WARM" value="WARM" />
          </el-select>
          <el-checkbox v-model="policyForm.recursive" style="margin-left:12px">递归</el-checkbox>
          <el-checkbox v-model="policyForm.runMover" style="margin-left:12px">执行 mover</el-checkbox>
        </template>
      </el-form-item>
      <el-form-item label="HAR 归档">
        <el-switch v-model="policyForm.har" />
        <template v-if="policyForm.har">
          <div style="margin-top:8px"></div>
          <el-input v-model="policyForm.harArchiveName" placeholder="category.har" style="width: 220px" />
          <el-input v-model="policyForm.harDestDir" placeholder="/archive/har/default" style="width: 300px; margin-left:12px" />
          <div style="font-size:12px;color:#909399;margin-top:6px">SSH 参数从“集群管理→HAR SSH 配置”读取</div>
        </template>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showPolicyDialog=false">取消</el-button>
      <el-button type="primary" @click="runArchiveStrategy">开始</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
  import { ref, onMounted, computed } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { ElMessage } from 'element-plus'
  import { tablesApi, type TableMetric } from '@/api/tables'
  import { tasksApi, type MergeTaskCreate } from '@/api/tasks'
  import { storageApi } from '@/api/storage'
  import { formatFileSize } from '@/utils/formatFileSize'
  import dayjs from 'dayjs'
  import TaskRunDialog from '@/components/TaskRunDialog.vue'

  const route = useRoute()
  const router = useRouter()

  const clusterId = computed(() => Number(route.params.clusterId))
  const database = computed(() => String(route.params.database))
  const tableName = computed(() => String(route.params.tableName))

  const loading = ref(false)
  const creating = ref(false)
  const showMergeDialog = ref(false)
  const tableMetric = ref<TableMetric | null>(null)
  const mergeSupported = ref<boolean>(true)
  const unsupportedReason = ref<string>('')

  // 分区小文件统计
  const partitionLoading = ref(false)
  const partitionError = ref('')
  const partitionItems = ref<any[]>([])
  const partitionTotal = ref(0)
  const partitionPage = ref(1)
  const partitionPageSize = ref(50)
  const partitionConcurrency = ref(5)

  const mergeForm = ref<MergeTaskCreate>({
    cluster_id: 0,
    task_name: '',
    table_name: '',
    database_name: '',
    partition_filter: '',
    merge_strategy: 'safe_merge'
  })

  // 合并范围与分区选择
  const mergeScope = ref<'table' | 'partition'>('table')
  const selectedPartition = ref<string>('')
  const partitionOptions = ref<string[]>([])

  const mergeRules = {
    task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }]
  }

  const mergeFormRef = ref()

  // 归档任务运行对话框
  const showRunDialog = ref(false)
  const runScanTaskId = ref<string | null>(null)
  const isArchived = computed(() => (tableMetric.value?.archive_status || '').toLowerCase() === 'archived')

  // 归档策略对话框与表单
  const showPolicyDialog = ref(false)
  const policyForm = ref({
    merge: false,
    mergeSingleFile: false,
    mergeTargetSizeMB: 512,
    storagePolicy: true,
    policy: 'COLD',
    recursive: true,
    ec: false,
    ecPolicy: 'RS-6-3-1024k',
    ecRecursive: true,
    runMover: false,
    har: false,
    harArchiveName: '',
    harDestDir: ''
  })
  const openArchivePolicy = () => {
    policyForm.value.merge = false
    policyForm.value.mergeSingleFile = false
    policyForm.value.mergeTargetSizeMB = 512
    policyForm.value.storagePolicy = true
    policyForm.value.policy = 'COLD'
    policyForm.value.recursive = true
    policyForm.value.runMover = false
    policyForm.value.ec = false
    policyForm.value.ecPolicy = 'RS-6-3-1024k'
    policyForm.value.ecRecursive = true
    policyForm.value.har = false
    const path = tableMetric.value?.table_path || ''
    const last = path.split('/').filter(Boolean).pop() || tableName.value
    policyForm.value.harArchiveName = `${last}.har`
    policyForm.value.harDestDir = `/archive/har/${database.value}`
    showPolicyDialog.value = true
  }

  const getHarSshDefaults = () => {
    try { const raw = localStorage.getItem(`har-ssh.${clusterId.value}`); return raw ? JSON.parse(raw) : null } catch { return null }
  }

  const runArchiveStrategy = async () => {
    if (!tableMetric.value) return
    try {
      const cid = clusterId.value
      const dbn = database.value
      const tbn = tableName.value
      const path = tableMetric.value.table_path
      const tasks: string[] = []
      // 0) 合并压缩（先进行，完成后再设置策略/EC/HAR）
      if ((policyForm.value as any).merge) {
        const targetBytes = (policyForm.value as any).mergeSingleFile ? -1 : Math.max(1, Number((policyForm.value as any).mergeTargetSizeMB || 512)) * 1024 * 1024
        const task = await tasksApi.create({
          cluster_id: cid,
          task_name: `merge_${dbn}_${tbn}_${Date.now()}`,
          table_name: tbn,
          database_name: dbn,
          partition_filter: '',
          merge_strategy: 'insert_overwrite',
          target_file_size: targetBytes
        } as any)
        await tasksApi.execute((task as any).id)
      }
      if (policyForm.value.storagePolicy) {
        const resp = await tablesApi.archiveTableWithProgress(cid, dbn, tbn, false, { mode: 'storage-policy', policy: policyForm.value.policy, recursive: policyForm.value.recursive })
        if ((resp as any)?.task_id) tasks.push((resp as any).task_id)
      }
      if (policyForm.value.ec) {
        const ssh = getHarSshDefaults()
        if (!ssh || !ssh.host) { ElMessage.warning('请先在集群管理维护 HAR SSH 配置'); }
        else {
          const ecResp = await storageApi.setEcPolicy(cid, { path, policy: policyForm.value.ecPolicy || 'RS-6-3-1024k', recursive: policyForm.value.ecRecursive, ssh_host: ssh.host, ssh_user: ssh.user || 'hdfs', ssh_port: ssh.port || 22, ssh_key_path: ssh.keyPath, kinit_principal: ssh.principal, kinit_keytab: ssh.keytab })
          if ((ecResp as any)?.task_id) tasks.push((ecResp as any).task_id)
        }
      }
      if (policyForm.value.runMover) {
        const ssh = getHarSshDefaults()
        if (!ssh || !ssh.host) { ElMessage.warning('请先在集群管理维护 HAR SSH 配置'); }
        else {
          const mover = await storageApi.runMover(cid, { path, ssh_host: ssh.host, ssh_user: ssh.user || 'hdfs', ssh_port: ssh.port || 22, ssh_key_path: ssh.keyPath, kinit_principal: ssh.principal, kinit_keytab: ssh.keytab })
          if ((mover as any)?.task_id) tasks.push((mover as any).task_id)
        }
      }
      if (policyForm.value.har) {
        const ssh = getHarSshDefaults()
        if (!ssh || !ssh.host) { ElMessage.warning('请先在集群管理维护 HAR SSH 配置'); }
        else {
          const { default: api } = await import('@/api/index')
          const seg = (path || '').split('/').filter(Boolean); const src = seg.pop() || tbn; const parent = '/' + seg.join('/')
          const payload = { archive_name: policyForm.value.harArchiveName || `${tbn}.har`, parent_path: parent, sources: [src], dest_dir: policyForm.value.harDestDir || `/archive/har/${dbn}`, replication: 3, ssh_host: ssh.host, ssh_user: ssh.user || 'hdfs', ssh_port: ssh.port || 22, ssh_key_path: ssh.keyPath, kinit_principal: ssh.principal, kinit_keytab: ssh.keytab, dry_run: false }
          const har = await api.post(`/har-archiving/create/${cid}`, payload)
          if ((har as any)?.task_id) tasks.push((har as any).task_id)
        }
      }
      showPolicyDialog.value = false
      if (tasks.length) { runScanTaskId.value = tasks[tasks.length - 1]; showRunDialog.value = true }
      ElMessage.success('归档策略任务已提交')
    } catch (e: any) {
      console.error('runArchiveStrategy failed', e); ElMessage.error(e?.message || '提交失败')
    }
  }

  const loadTableInfo = async () => {
    loading.value = true
    try {
      // Limit scope to current database to avoid large cluster-wide queries blocking the UI
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
          merge_strategy: 'safe_merge'
        }
        // 若是分区表，加载分区列表供选择
        if (tableMetric.value.is_partitioned) {
          try {
            const resp = await tasksApi.getTablePartitions(
              clusterId.value,
              database.value,
              tableName.value
            )
            const parts = (resp?.partitions || resp || []) as string[]
            partitionOptions.value = parts
          } catch (e) {
            partitionOptions.value = []
          }
        } else {
          mergeScope.value = 'table'
          partitionOptions.value = []
        }
        // 加载表的更多信息（含是否支持合并）
        try {
          const info = await tasksApi.getTableInfo(clusterId.value, database.value, tableName.value)
          // 默认支持合并；仅当明确返回 false 时禁用
          if (info && Object.prototype.hasOwnProperty.call(info, 'merge_supported')) {
            mergeSupported.value = info.merge_supported !== false
          } else {
            mergeSupported.value = true
          }
          unsupportedReason.value =
            info?.unsupported_reason && info.merge_supported === false
              ? info.unsupported_reason
              : ''
        } catch (e: any) {
          // 获取失败时保持默认（支持），并在真正执行时有后端兜底的严格校验
          mergeSupported.value = true
          unsupportedReason.value = ''
        }
      }
    } catch (error) {
      console.error('Failed to load table info:', error)
      ElMessage.error('加载表信息失败')
    } finally {
      loading.value = false
    }
  }

  const refreshTableInfo = async () => {
    try {
      await tablesApi.triggerScan(clusterId.value)
      ElMessage.success('扫描任务已启动')
      setTimeout(() => {
        loadTableInfo()
      }, 2000)
    } catch (error) {
      console.error('Failed to trigger scan:', error)
      ElMessage.error('触发扫描失败')
    }
  }

  const archiveTableBg = async (mode: 'move' | 'storage-policy' = 'storage-policy') => {
    if (!tableMetric.value) return
    try {
      const resp = await tablesApi.archiveTableWithProgress(
        clusterId.value,
        database.value,
        tableName.value,
        false,
        mode === 'storage-policy' ? { mode: 'storage-policy', policy: 'COLD', recursive: true } : { mode: 'move' }
      )
      const taskId = (resp as any)?.task_id
      if (taskId) {
        runScanTaskId.value = taskId
        showRunDialog.value = true
      }
      ElMessage.success(mode === 'storage-policy' ? '策略归档任务已提交' : '目录迁移归档任务已提交')
    } catch (e: any) {
      console.error('archiveTableBg failed', e)
      ElMessage.error(e?.message || '提交归档任务失败')
    }
  }

  // 目录迁移归档已移除，仅保留存储策略归档

  const restoreTableBg = async () => {
    if (!tableMetric.value) return
    try {
      const resp = await tablesApi.restoreTableWithProgress(
        clusterId.value,
        database.value,
        tableName.value
      )
      const taskId = (resp as any)?.task_id
      if (taskId) {
        runScanTaskId.value = taskId
        showRunDialog.value = true
      }
      ElMessage.success('恢复任务已提交')
    } catch (e: any) {
      console.error('restoreTableBg failed', e)
      ElMessage.error(e?.message || '提交恢复任务失败')
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
    } catch (e: any) {
      console.error('Failed to load partition metrics:', e)
      partitionError.value = e?.message || '加载分区统计失败'
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
      await mergeFormRef.value.validate()
      creating.value = true
      // 根据合并范围设置 partition_filter 与默认策略
      if (tableMetric.value?.is_partitioned && mergeScope.value === 'partition') {
        if (!selectedPartition.value) {
          ElMessage.warning('请选择分区')
          creating.value = false
          return
        }
        mergeForm.value.partition_filter = specToFilter(selectedPartition.value)
        if (!mergeForm.value.merge_strategy || mergeForm.value.merge_strategy === 'safe_merge') {
          mergeForm.value.merge_strategy = 'insert_overwrite'
        }
      } else {
        mergeForm.value.partition_filter = ''
        if (!mergeForm.value.merge_strategy) mergeForm.value.merge_strategy = 'safe_merge'
      }

      const task = await tasksApi.create(mergeForm.value)
      await tasksApi.execute(task.id)

      ElMessage.success('合并任务已创建并启动')
      showMergeDialog.value = false

      router.push('/tasks')
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
      } catch (e) {
        partitionOptions.value = []
      }
    }
    mergeScope.value = tableMetric.value?.is_partitioned ? 'partition' : 'table'
    selectedPartition.value = ''
    showMergeDialog.value = true
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

  const formatTime = (time: string): string => {
    return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
  }

  const getProgressColor = (percentage: number): string => {
    if (percentage > 80) return '#f56c6c'
    if (percentage > 50) return '#e6a23c'
    if (percentage > 20) return '#1989fa'
    return '#67c23a'
  }

  const getTableTypeColor = (tableType: string): string => {
    switch (tableType) {
      case 'MANAGED_TABLE':
        return 'success'
      case 'EXTERNAL_TABLE':
        return 'warning'
      case 'VIEW':
        return 'info'
      default:
        return ''
    }
  }

  const formatTableType = (tableType: string): string => {
    switch (tableType) {
      case 'MANAGED_TABLE':
        return '托管表'
      case 'EXTERNAL_TABLE':
        return '外部表'
      case 'VIEW':
        return '视图'
      default:
        return tableType || '未知'
    }
  }

  const getSmallFileRatio = (): number => {
    if (!tableMetric.value || tableMetric.value.total_files === 0) return 0
    return Math.round((tableMetric.value.small_files / tableMetric.value.total_files) * 100)
  }

  const getSmallFileSeverity = (): string => {
    const ratio = getSmallFileRatio()
    if (ratio >= 80) return 'error'
    if (ratio >= 50) return 'warning'
    return 'info'
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

    const suggestions = []
    const ratio = getSmallFileRatio()

    if (ratio >= 80) {
      suggestions.push('立即执行安全合并策略，可提升查询性能50%+')
      suggestions.push('考虑调整数据写入方式，避免产生更多小文件')
    } else if (ratio >= 50) {
      suggestions.push('使用安全合并策略进行文件合并')
      suggestions.push('建议在业务低峰期执行合并任务')
    } else {
      suggestions.push('可选择性进行文件合并优化')
      suggestions.push('监控后续数据写入，防止小文件累积')
    }

    if (tableMetric.value.is_partitioned) {
      suggestions.push('分区表可按分区逐步进行合并，降低对业务的影响')
    }

    if (tableMetric.value.storage_format === 'TEXT') {
      suggestions.push('考虑转换为 ORC 或 Parquet 格式以获得更好性能')
    }

    return suggestions
  }

  const getStorageFormatAdvice = (): string | null => {
    if (!tableMetric.value) return null

    const format = tableMetric.value.storage_format
    const totalSize = tableMetric.value.total_size

    if (format === 'TEXT') {
      if (totalSize > 100 * 1024 * 1024) {
        // > 100MB
        return `当前使用 TEXT 格式，建议转换为 ORC 或 Parquet 格式。预计可减少存储空间 30-50%，提升查询性能 2-5 倍。`
      }
      return `TEXT 格式适合小数据量，但不支持列式存储优化。考虑升级到 ORC 或 Parquet。`
    }

    if (format === 'SEQUENCE' || format === 'AVRO') {
      return `${format} 格式功能完整但性能不如 ORC/Parquet。建议评估转换到列式存储格式的可行性。`
    }

    if (format === 'ORC' || format === 'PARQUET') {
      return null // 已经是最优格式
    }

    return `建议评估当前 ${format} 格式是否为最佳选择，考虑 ORC 或 Parquet 格式的性能优势。`
  }

  const getPartitionAdvice = (): string | null => {
    if (!tableMetric.value) return null

    const { is_partitioned, partition_count, total_files, total_size } = tableMetric.value

    if (!is_partitioned) {
      if (total_size > 1024 * 1024 * 1024) {
        // > 1GB
        return '大表建议考虑分区策略，可显著提升查询性能。常用分区键：日期、地区、业务类型等。'
      }
      return null
    }

    if (partition_count > 10000) {
      return `分区数量过多（${partition_count}个），可能导致元数据压力。建议合并小分区或调整分区策略。`
    }

    if (partition_count > 0 && total_files / partition_count < 5) {
      return '平均每个分区文件数过少，建议合并小分区或调整数据写入策略。'
    }

    return null
  }

  onMounted(() => {
    loadTableInfo()
    // 延迟加载分区详情，避免与表信息并发冲突
    setTimeout(() => loadPartitionMetrics(), 0)
  })
</script>

<style scoped>
  .breadcrumb-container {
    margin-bottom: 20px;
  }

  .table-info-card {
    margin-bottom: 20px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header-actions {
    display: flex;
    gap: 8px;
  }

  .loading-container {
    padding: 20px;
  }

  .table-info-content {
    padding: 20px 0;
  }

  .info-section {
    margin-bottom: 32px;
  }

  .info-section h3 {
    margin-bottom: 16px;
    color: #303133;
    font-size: 16px;
    font-weight: 600;
  }

  .statistic-item {
    text-align: left;
  }

  .statistic-title {
    font-size: 14px;
    color: #909399;
    margin-bottom: 8px;
  }

  .no-data {
    padding: 40px;
    text-align: center;
  }

  .dialog-footer {
    text-align: right;
  }

  :deep(.el-statistic__content) {
    font-size: 24px;
    font-weight: 600;
  }

  :deep(.el-statistic__title) {
    font-size: 14px;
    color: #909399;
    margin-bottom: 8px;
  }

  :deep(.el-alert ul) {
    margin: 8px 0 0 20px;
  }

  :deep(.el-alert li) {
    margin-bottom: 4px;
  }

  .recommendations {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .recommendation-content {
    font-size: 14px;
    line-height: 1.5;
  }

  .recommendation-content p {
    margin: 8px 0;
  }

  .recommendation-content ul {
    margin: 8px 0 0 20px;
    padding-left: 0;
  }

  .recommendation-content li {
    margin-bottom: 6px;
    color: #606266;
  }

  .partitions-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .partitions-summary {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    color: #606266;
  }

  .partitions-actions {
    margin-top: 10px;
    text-align: center;
  }
</style>
.concurrency-control { display: inline-flex; align-items: center; gap: 6px; } .concurrency-control
.label { color: #606266; font-size: 12px; }
