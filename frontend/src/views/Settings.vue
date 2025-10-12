<template>
  <div class="settings-management">
    <!-- Cloudera风格页面头部 -->
    <div class="header-section">
      <div class="title-section">
        <h1>系统设置</h1>
        <p>配置和管理您的DataNova平台系统参数</p>
      </div>
      <div class="actions-section">
        <el-button
          @click="checkSystemHealth"
          class="cloudera-btn secondary"
        >
          <el-icon><Refresh /></el-icon>
          刷新状态
        </el-button>
        <el-button
          @click="saveSettings"
          class="cloudera-btn primary"
        >
          <el-icon><Check /></el-icon>
          保存设置
        </el-button>
      </div>
    </div>

    <!-- Cloudera风格系统状态概览 -->
    <div class="cloudera-metrics-grid stagger-animation">
      <div
        class="cloudera-metric-card stagger-item"
        style="--stagger-delay: 0.1s"
      >
        <div class="metric-header">
          <div class="metric-icon info">
            <el-icon><Monitor /></el-icon>
          </div>
          <div class="metric-status">
            <div
              class="status-dot"
              :class="systemInfo.db_connected ? 'success' : 'danger'"
            ></div>
          </div>
        </div>
        <div class="metric-value">{{ systemInfo.version }}</div>
        <div class="metric-label">系统版本</div>
        <div class="metric-subtext">环境：{{ systemInfo.environment }}</div>
      </div>

      <div
        class="cloudera-metric-card stagger-item"
        style="--stagger-delay: 0.2s"
      >
        <div class="metric-header">
          <div class="metric-icon success">
            <el-icon><Timer /></el-icon>
          </div>
        </div>
        <div class="metric-value">{{ systemInfo.uptime }}</div>
        <div class="metric-label">运行时间</div>
      </div>

      <div
        class="cloudera-metric-card stagger-item"
        style="--stagger-delay: 0.3s"
      >
        <div class="metric-header">
          <div
            class="metric-icon"
            :class="systemInfo.db_connected ? 'success' : 'danger'"
          >
            <el-icon><Connection /></el-icon>
          </div>
          <div class="metric-status">
            <div
              class="status-dot"
              :class="systemInfo.db_connected ? 'success' : 'danger'"
            ></div>
          </div>
        </div>
        <div class="metric-value">{{ systemInfo.db_connected ? '正常' : '异常' }}</div>
        <div class="metric-label">数据库连接</div>
      </div>

      <div
        class="cloudera-metric-card stagger-item"
        style="--stagger-delay: 0.4s"
      >
        <div class="metric-header">
          <div
            class="metric-icon"
            :class="systemInfo.celery_active ? 'warning' : 'danger'"
          >
            <el-icon><Operation /></el-icon>
          </div>
          <div class="metric-status">
            <div
              class="status-dot"
              :class="systemInfo.celery_active ? 'success' : 'warning'"
            ></div>
          </div>
        </div>
        <div class="metric-value">{{ systemInfo.celery_active ? '运行中' : '未启动' }}</div>
        <div class="metric-label">Celery状态</div>
      </div>
    </div>

    <!-- Cloudera风格设置面板 -->
    <div class="cloudera-tabs">
      <div class="tab-nav">
        <div
          v-for="tab in tabs"
          :key="tab.key"
          :class="['tab-item', { active: activeTab === tab.key }]"
          @click="activeTab = tab.key"
        >
          <el-icon><component :is="tab.icon" /></el-icon>
          <span>{{ tab.label }}</span>
        </div>
      </div>

      <div class="tab-content">
        <!-- 扫描配置标签页 -->
        <div
          v-show="activeTab === 'scan'"
          class="tab-pane"
        >
          <div class="cloudera-form-panel">
            <div class="panel-header">
              <h3>扫描配置</h3>
              <p>配置集群扫描的默认参数和行为</p>
            </div>

            <el-form
              :model="scanSettings"
              label-width="150px"
              class="cloudera-form"
            >
              <el-form-item label="默认扫描间隔">
                <el-input-number
                  v-model="scanSettings.scan_interval"
                  :min="1"
                  :max="24"
                  controls-position="right"
                  class="cloudera-input-number"
                />
                <span class="input-suffix">小时</span>
                <div class="form-help">自动扫描集群小文件的时间间隔</div>
              </el-form-item>

              <el-form-item label="扫描并发数">
                <el-input-number
                  v-model="scanSettings.max_workers"
                  :min="1"
                  :max="16"
                  controls-position="right"
                  class="cloudera-input-number"
                />
                <div class="form-help">同时扫描的最大线程数</div>
              </el-form-item>

              <el-form-item label="扫描超时时间">
                <el-input-number
                  v-model="scanSettings.scan_timeout"
                  :min="60"
                  :max="3600"
                  controls-position="right"
                  class="cloudera-input-number"
                />
                <span class="input-suffix">秒</span>
                <div class="form-help">单个表扫描的超时时间</div>
              </el-form-item>
            </el-form>
          </div>
        </div>

        <!-- 合并配置标签页 -->
        <div
          v-show="activeTab === 'merge'"
          class="tab-pane"
        >
          <div class="cloudera-form-panel">
            <div class="panel-header">
              <h3>合并配置</h3>
              <p>配置小文件合并任务的默认策略和参数</p>
            </div>

            <el-form
              :model="mergeSettings"
              label-width="150px"
              class="cloudera-form"
            >
              <el-form-item label="合并策略">
                <div class="form-field">
                  <el-tag type="success" size="large">统一安全合并 (UNIFIED_SAFE_MERGE)</el-tag>
                  <div class="form-help">系统统一使用安全合并策略，确保零停机时间</div>
                </div>
              </el-form-item>

              <el-form-item label="目标文件大小">
                <el-input-number
                  v-model="mergeSettings.target_file_size"
                  :min="64"
                  :max="1024"
                  controls-position="right"
                  class="cloudera-input-number"
                />
                <span class="input-suffix">MB</span>
                <div class="form-help">合并后的目标文件大小</div>
              </el-form-item>

              <el-form-item label="最大合并文件数">
                <el-input-number
                  v-model="mergeSettings.max_files_per_task"
                  :min="10"
                  :max="10000"
                  controls-position="right"
                  class="cloudera-input-number"
                />
                <div class="form-help">单个任务最多合并的文件数量</div>
              </el-form-item>
            </el-form>
          </div>
        </div>

        <!-- 告警配置标签页 -->
        <div
          v-show="activeTab === 'alert'"
          class="tab-pane"
        >
          <div class="cloudera-form-panel">
            <div class="panel-header">
              <h3>告警配置</h3>
              <p>配置小文件告警的阈值和通知方式</p>
            </div>

            <el-form
              :model="alertSettings"
              label-width="150px"
              class="cloudera-form"
            >
              <el-form-item label="小文件告警阈值">
                <el-input-number
                  v-model="alertSettings.small_file_threshold"
                  :min="100"
                  :max="100000"
                  controls-position="right"
                  class="cloudera-input-number"
                />
                <div class="form-help">单表小文件数量超过此值时发送告警</div>
              </el-form-item>

              <el-form-item label="小文件占比告警">
                <el-input-number
                  v-model="alertSettings.small_file_ratio_threshold"
                  :min="10"
                  :max="100"
                  controls-position="right"
                  class="cloudera-input-number"
                />
                <span class="input-suffix">%</span>
                <div class="form-help">小文件占比超过此值时发送告警</div>
              </el-form-item>

              <el-form-item label="启用邮件告警">
                <el-switch
                  v-model="alertSettings.email_enabled"
                  class="cloudera-switch"
                  active-text="开启"
                  inactive-text="关闭"
                />
                <div class="form-help">开启后会向指定邮箱发送告警通知</div>
              </el-form-item>

              <el-form-item
                v-if="alertSettings.email_enabled"
                label="收件人列表"
              >
                <el-input
                  v-model="alertSettings.email_recipients"
                  type="textarea"
                  placeholder="多个邮箱用逗号分隔，例如：admin@company.com, ops@company.com"
                  :rows="3"
                  class="cloudera-textarea"
                />
                <div class="form-help">告警邮件的接收者列表</div>
              </el-form-item>
            </el-form>
          </div>
        </div>

        <!-- 系统信息标签页 -->
        <div
          v-show="activeTab === 'system'"
          class="tab-pane"
        >
          <div class="cloudera-form-panel">
            <div class="panel-header">
              <h3>系统信息</h3>
              <p>查看系统状态和基本信息</p>
            </div>

            <el-descriptions
              title="系统详细状态"
              :column="2"
              border
              class="cloudera-descriptions"
            >
              <el-descriptions-item label="系统版本">
                <el-tag
                  type="info"
                  class="cloudera-tag"
                  >{{ systemInfo.version }}</el-tag
                >
              </el-descriptions-item>
              <el-descriptions-item label="运行时间">{{ systemInfo.uptime }}</el-descriptions-item>
              <el-descriptions-item label="Python 版本">{{
                systemInfo.python_version
              }}</el-descriptions-item>
              <el-descriptions-item label="数据库连接">
                <el-tag
                  :type="systemInfo.db_connected ? 'success' : 'danger'"
                  class="cloudera-tag"
                >
                  {{ systemInfo.db_connected ? '正常' : '异常' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Redis 连接">
                <el-tag
                  :type="systemInfo.redis_connected ? 'success' : 'danger'"
                  class="cloudera-tag"
                >
                  {{ systemInfo.redis_connected ? '正常' : '异常' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Celery 状态">
                <el-tag
                  :type="systemInfo.celery_active ? 'success' : 'warning'"
                  class="cloudera-tag"
                >
                  {{ systemInfo.celery_active ? '运行中' : '未启动' }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>

            <div class="system-actions">
              <el-button
                @click="checkSystemHealth"
                class="cloudera-btn primary"
              >
                <el-icon><Refresh /></el-icon>
                刷新系统状态
              </el-button>
              <el-button
                @click="exportConfig"
                class="cloudera-btn success"
              >
                <el-icon><Download /></el-icon>
                导出配置
              </el-button>
              <el-button
                @click="clearCache"
                class="cloudera-btn warning"
              >
                <el-icon><Delete /></el-icon>
                清理缓存
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Cloudera风格操作按钮 -->
    <div class="settings-footer">
      <el-button
        @click="resetSettings"
        class="cloudera-btn secondary"
      >
        <el-icon><RefreshLeft /></el-icon>
        重置设置
      </el-button>
      <el-button
        @click="saveSettings"
        class="cloudera-btn primary"
      >
        <el-icon><Check /></el-icon>
        保存所有设置
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref, onMounted } from 'vue'
  import { ElMessage } from 'element-plus'
  import {
    Check,
    Refresh,
    Monitor,
    Timer,
    Connection,
    Operation,
    Download,
    Delete,
    RefreshLeft
  } from '@element-plus/icons-vue'
  import { systemApi } from '@/api/system'
  import { useGlobalRefresh } from '@/composables/useGlobalRefresh'

  const activeTab = ref('scan')

  // 标签页配置
  const tabs = [
    { key: 'scan', label: '扫描配置', icon: 'Monitor' },
    { key: 'merge', label: '合并配置', icon: 'Operation' },
    { key: 'alert', label: '告警配置', icon: 'Bell' },
    { key: 'system', label: '系统信息', icon: 'InfoFilled' }
  ]

  // 设置数据
  const scanSettings = ref({
    scan_interval: 6,
    max_workers: 4,
    scan_timeout: 300
  })

  const mergeSettings = ref({
    default_strategy: 'safe_merge',
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
    uptime: '检测中',
    python_version: '3.11',
    db_connected: true,
    redis_connected: true,
    celery_active: true,
    environment: 'development'
  })
  const systemStatus = ref({
    api_status: 'unknown',
    database_status: 'unknown',
    redis_status: 'unknown',
    celery_active: false
  })

  // 方法
  const saveSettings = async () => {
    try {
      const settingsData = {
        scan: scanSettings.value,
        merge: mergeSettings.value,
        alert: alertSettings.value
      }
      
      // 保存设置到后端（目前使用localStorage模拟）
      localStorage.setItem('hive-platform-settings', JSON.stringify(settingsData))
      ElMessage.success('所有设置已保存成功')
    } catch (error) {
      console.error('保存设置失败:', error)
      ElMessage.error('保存设置失败，请重试')
    }
  }

  const resetSettings = () => {
    // 重置为默认值
    const defaultSettings = {
      scan: {
        scan_interval: 6,
        max_workers: 4,
        scan_timeout: 300
      },
      merge: {
        default_strategy: 'safe_merge',
        target_file_size: 256,
        max_files_per_task: 1000
      },
      alert: {
        small_file_threshold: 1000,
        small_file_ratio_threshold: 80,
        email_enabled: false,
        email_recipients: ''
      }
    }
    
    scanSettings.value = defaultSettings.scan
    mergeSettings.value = defaultSettings.merge
    alertSettings.value = defaultSettings.alert
    
    // 清除本地存储的设置
    localStorage.removeItem('hive-platform-settings')
    ElMessage.info('所有设置已重置为默认值')
  }

  const checkSystemHealth = async () => {
    const loadingMessage = ElMessage({
      message: '正在检查系统状态...',
      type: 'info',
      duration: 0
    })

    try {
      const response = await systemApi.getHealth()

      systemStatus.value = {
        api_status: response.status || 'unknown',
        database_status: response.status === 'healthy' ? 'connected' : 'unknown',
        redis_status: response.status === 'healthy' ? 'connected' : 'unknown',
        celery_active: response.status === 'healthy'
      }

      systemInfo.value = {
        ...systemInfo.value,
        uptime: response.status === 'healthy' ? '运行中' : '检测失败',
        environment: response.server_config?.environment || 'unknown'
      }

      ElMessage.success('系统状态检查完成')
    } catch (error) {
      console.error('系统健康检查失败:', error)
      systemStatus.value = {
        api_status: 'unhealthy',
        database_status: 'unknown',
        redis_status: 'unknown',
        celery_active: false
      }
      ElMessage.error('系统健康检查失败，请检查服务状态')
    } finally {
      loadingMessage.close()
    }
  }

  const exportConfig = () => {
    // 导出配置文件
    const config = {
      scan: scanSettings.value,
      merge: mergeSettings.value,
      alert: alertSettings.value,
      system: systemStatus.value,
      export_time: new Date().toISOString(),
      version: '1.0.0'
    }

    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: 'application/json'
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `hive-platform-config-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)

    ElMessage.success('配置文件已导出')
  }

  const clearCache = () => {
    // 清理系统缓存
    const loadingMessage = ElMessage({
      message: '正在清理系统缓存...',
      type: 'info',
      duration: 0
    })

    try {
      // 清理浏览器缓存
      localStorage.clear()
      sessionStorage.clear()
      
      // 清理应用特定的缓存
      const cacheKeys = ['hive-platform-settings', 'dashboard-cache', 'cluster-cache']
      cacheKeys.forEach(key => {
        localStorage.removeItem(key)
        sessionStorage.removeItem(key)
      })
      
      setTimeout(() => {
        loadingMessage.close()
        ElMessage.success('系统缓存已清理完成')
      }, 1500)
    } catch (error) {
      loadingMessage.close()
      console.error('缓存清理失败:', error)
      ElMessage.error('缓存清理失败，请重试')
    }
  }

  onMounted(async () => {
    try {
      const savedSettings = localStorage.getItem('hive-platform-settings')
      if (savedSettings) {
        const parsedSettings = JSON.parse(savedSettings)

        if (parsedSettings.scan) {
          scanSettings.value = { ...scanSettings.value, ...parsedSettings.scan }
        }
        if (parsedSettings.merge) {
          mergeSettings.value = { ...mergeSettings.value, ...parsedSettings.merge }
        }
        if (parsedSettings.alert) {
          alertSettings.value = { ...alertSettings.value, ...parsedSettings.alert }
        }
      }
    } catch (error) {
      console.error('加载设置数据失败:', error)
    }

    await checkSystemHealth()
  })

  useGlobalRefresh(async () => {
    await checkSystemHealth()
  })
</script>

<style scoped>
  .settings-management {
    padding: var(--space-3) var(--space-4) var(--space-8) var(--space-4);
    min-height: 100vh;
    overflow-y: visible;
    background: var(--bg-app);
  }

  .header-section {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--space-8);
    padding: var(--space-6);
    background: var(--bg-primary);
    border-radius: var(--radius-xl);
    border: 1px solid var(--gray-200);
    box-shadow: var(--elevation-1);
  }

  .title-section h1 {
    margin: 0 0 var(--space-2) 0;
    font-size: var(--text-3xl);
    font-weight: var(--font-bold);
    color: var(--gray-900);
  }

  .title-section p {
    margin: 0;
    color: var(--gray-600);
    font-size: var(--text-lg);
  }

  .actions-section {
    display: flex;
    gap: var(--space-4);
    align-items: center;
  }

  /* Cloudera风格标签页 */
  .cloudera-tabs {
    background: var(--bg-primary);
    border-radius: var(--radius-xl);
    border: 1px solid var(--gray-200);
    box-shadow: var(--elevation-1);
    overflow: hidden;
    margin-bottom: var(--space-8);
  }

  .tab-nav {
    display: flex;
    background: var(--gray-50);
    border-bottom: 1px solid var(--gray-200);
  }

  .tab-item {
    flex: 1;
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-4) var(--space-6);
    cursor: pointer;
    transition: all var(--transition-fast);
    font-weight: var(--font-medium);
    color: var(--gray-600);
    border-right: 1px solid var(--gray-200);
  }

  .tab-item:last-child {
    border-right: none;
  }

  .tab-item:hover {
    background: var(--gray-100);
    color: var(--gray-900);
  }

  .tab-item.active {
    background: var(--primary-50);
    color: var(--primary-600);
    border-bottom: 3px solid var(--primary-500);
  }

  .tab-content {
    padding: var(--space-6);
  }

  .tab-pane {
    animation: fadeIn 0.3s ease-in-out;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  /* Cloudera风格表单面板 */
  .metric-subtext {
    margin-top: 4px;
    font-size: 12px;
    color: #8f9bb3;
  }

  .cloudera-form-panel {
    background: var(--bg-primary);
    border-radius: var(--radius-xl);
    border: 1px solid var(--gray-200);
    box-shadow: var(--elevation-1);
    overflow: hidden;
  }

  .panel-header {
    padding: var(--space-6);
    background: var(--gray-50);
    border-bottom: 1px solid var(--gray-200);
  }

  .panel-header h3 {
    margin: 0 0 var(--space-2) 0;
    font-size: var(--text-xl);
    font-weight: var(--font-semibold);
    color: var(--gray-900);
  }

  .panel-header p {
    margin: 0;
    color: var(--gray-600);
    font-size: var(--text-sm);
  }

  .cloudera-form {
    padding: var(--space-6);
  }

  .cloudera-form .el-form-item {
    margin-bottom: var(--space-6);
  }

  .cloudera-input-number {
    width: 200px;
  }

  .input-suffix {
    margin-left: var(--space-2);
    color: var(--gray-600);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
  }

  .cloudera-radio-group {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .cloudera-radio {
    margin-right: 0;
    margin-bottom: 0;
  }

  .cloudera-switch {
    transform: scale(1.2);
  }

  .cloudera-textarea {
    width: 100%;
  }

  .form-help {
    font-size: var(--text-xs);
    color: var(--gray-500);
    margin-top: var(--space-2);
    line-height: var(--leading-relaxed);
  }

  .cloudera-descriptions {
    margin-bottom: var(--space-6);
  }

  .cloudera-tag {
    font-weight: var(--font-medium);
  }

  .system-actions {
    display: flex;
    gap: var(--space-4);
    flex-wrap: wrap;
  }

  .settings-footer {
    display: flex;
    justify-content: center;
    gap: var(--space-6);
    padding: var(--space-6);
    background: var(--bg-primary);
    border-radius: var(--radius-xl);
    border: 1px solid var(--gray-200);
    box-shadow: var(--elevation-1);
  }

  /* 依次出现动画 */
  .stagger-animation {
    perspective: 1000px;
  }

  .stagger-item {
    animation: staggerIn 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
    opacity: 0;
    transform: translateY(30px) scale(0.95);
    animation-delay: var(--stagger-delay, 0s);
  }

  .stagger-item:hover {
    transform: translateY(-4px) scale(1.02);
    box-shadow: var(--elevation-4);
  }

  @keyframes staggerIn {
    0% {
      opacity: 0;
      transform: translateY(30px) scale(0.95);
    }
    60% {
      opacity: 0.8;
      transform: translateY(-5px) scale(1.02);
    }
    100% {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  /* 响应式调整 */
  @media (max-width: 1200px) {
    .cloudera-metrics-grid {
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: var(--space-4);
    }

    .cloudera-form {
      padding: var(--space-4);
    }
  }

  @media (max-width: 768px) {
    .settings-management {
      padding: var(--space-4);
    }

    .header-section {
      flex-direction: column;
      gap: var(--space-4);
      text-align: center;
    }

    .cloudera-metrics-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    .tab-nav {
      flex-direction: column;
    }

    .tab-item {
      border-right: none;
      border-bottom: 1px solid var(--gray-200);
    }

    .tab-item:last-child {
      border-bottom: none;
    }

    .cloudera-radio-group {
      gap: var(--space-2);
    }

    .system-actions {
      flex-direction: column;
      align-items: stretch;
    }

    .settings-footer {
      flex-direction: column;
      align-items: stretch;
    }

    .cloudera-input-number {
      width: 100%;
    }
  }
</style>
