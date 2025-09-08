<template>
  <div class="settings">
    <el-card>
      <template #header>
        <span>系统设置</span>
      </template>

      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="扫描配置" name="scan">
          <el-form :model="scanSettings" label-width="150px">
            <el-form-item label="默认扫描间隔">
              <el-input-number
                v-model="scanSettings.scan_interval"
                :min="1"
                :max="24"
                append="小时"
              />
              <div class="form-help">自动扫描集群小文件的时间间隔</div>
            </el-form-item>
            
            <el-form-item label="扫描并发数">
              <el-input-number
                v-model="scanSettings.max_workers"
                :min="1"
                :max="16"
              />
              <div class="form-help">同时扫描的最大线程数</div>
            </el-form-item>
            
            <el-form-item label="扫描超时时间">
              <el-input-number
                v-model="scanSettings.scan_timeout"
                :min="60"
                :max="3600"
                append="秒"
              />
              <div class="form-help">单个表扫描的超时时间</div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="合并配置" name="merge">
          <el-form :model="mergeSettings" label-width="150px">
            <el-form-item label="默认合并策略">
              <el-radio-group v-model="mergeSettings.default_strategy">
                <el-radio label="concatenate">文件合并 (CONCATENATE)</el-radio>
                <el-radio label="insert_overwrite">重写插入 (INSERT OVERWRITE)</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item label="目标文件大小">
              <el-input-number
                v-model="mergeSettings.target_file_size"
                :min="64"
                :max="1024"
                append="MB"
              />
              <div class="form-help">合并后的目标文件大小</div>
            </el-form-item>
            
            <el-form-item label="最大合并文件数">
              <el-input-number
                v-model="mergeSettings.max_files_per_task"
                :min="10"
                :max="10000"
              />
              <div class="form-help">单个任务最多合并的文件数量</div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="告警配置" name="alert">
          <el-form :model="alertSettings" label-width="150px">
            <el-form-item label="小文件告警阈值">
              <el-input-number
                v-model="alertSettings.small_file_threshold"
                :min="100"
                :max="100000"
              />
              <div class="form-help">单表小文件数量超过此值时发送告警</div>
            </el-form-item>
            
            <el-form-item label="小文件占比告警">
              <el-input-number
                v-model="alertSettings.small_file_ratio_threshold"
                :min="10"
                :max="100"
                append="%"
              />
              <div class="form-help">小文件占比超过此值时发送告警</div>
            </el-form-item>
            
            <el-form-item label="启用邮件告警">
              <el-switch v-model="alertSettings.email_enabled" />
            </el-form-item>
            
            <el-form-item v-if="alertSettings.email_enabled" label="收件人列表">
              <el-input
                v-model="alertSettings.email_recipients"
                type="textarea"
                placeholder="多个邮箱用逗号分隔"
              />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="系统信息" name="system">
          <el-descriptions title="系统状态" :column="2" border>
            <el-descriptions-item label="系统版本">{{ systemInfo.version }}</el-descriptions-item>
            <el-descriptions-item label="运行时间">{{ systemInfo.uptime }}</el-descriptions-item>
            <el-descriptions-item label="Python 版本">{{ systemInfo.python_version }}</el-descriptions-item>
            <el-descriptions-item label="数据库连接">
              <el-tag :type="systemInfo.db_connected ? 'success' : 'danger'">
                {{ systemInfo.db_connected ? '正常' : '异常' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Redis 连接">
              <el-tag :type="systemInfo.redis_connected ? 'success' : 'danger'">
                {{ systemInfo.redis_connected ? '正常' : '异常' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Celery 状态">
              <el-tag :type="systemInfo.celery_active ? 'success' : 'warning'">
                {{ systemInfo.celery_active ? '运行中' : '未启动' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <div style="margin-top: 20px;">
            <el-button type="primary" @click="checkSystemHealth">刷新系统状态</el-button>
            <el-button type="success" @click="exportConfig">导出配置</el-button>
            <el-button type="warning" @click="clearCache">清理缓存</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>

      <div class="settings-footer">
        <el-button type="primary" @click="saveSettings">保存设置</el-button>
        <el-button @click="resetSettings">重置</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const activeTab = ref('scan')

// 设置数据
const scanSettings = ref({
  scan_interval: 6,
  max_workers: 4,
  scan_timeout: 300
})

const mergeSettings = ref({
  default_strategy: 'concatenate',
  target_file_size: 256,
  max_files_per_task: 1000
})

const alertSettings = ref({
  small_file_threshold: 1000,
  small_file_ratio_threshold: 80,
  email_enabled: false,
  email_recipients: ''
})

const systemInfo = ref({
  version: '1.0.0',
  uptime: '2 天 3 小时',
  python_version: '3.9.0',
  db_connected: true,
  redis_connected: true,
  celery_active: true
})

// 方法
const saveSettings = () => {
  // TODO: 保存设置到后端
  ElMessage.success('设置保存成功')
}

const resetSettings = () => {
  // TODO: 重置为默认值
  ElMessage.info('设置已重置')
}

const checkSystemHealth = () => {
  // TODO: 检查系统健康状态
  ElMessage.success('系统状态已刷新')
}

const exportConfig = () => {
  // TODO: 导出配置文件
  ElMessage.info('配置导出功能开发中')
}

const clearCache = () => {
  // TODO: 清理系统缓存
  ElMessage.success('缓存已清理')
}

onMounted(() => {
  // TODO: 加载设置数据
})
</script>

<style scoped>
.settings {
  max-width: 800px;
}

.form-help {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.settings-footer {
  margin-top: 30px;
  text-align: center;
  border-top: 1px solid #ebeef5;
  padding-top: 20px;
}
</style>