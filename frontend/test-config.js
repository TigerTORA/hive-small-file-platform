// 测试配置文件
const TEST_CONFIG = {
  // 应用配置
  app: {
    baseUrl: 'http://localhost:3002',
    apiBaseUrl: 'http://localhost:8000',
    timeout: 30000,
    retryAttempts: 3
  },

  // 页面路由
  routes: {
    clusters: '/#/clusters',
    dashboard: '/#/dashboard',
    tables: '/#/tables',
    tasks: '/#/tasks',
    settings: '/#/settings',
    clusterDetail: '/#/clusters/{id}',
    tableDetail: '/#/tables/{clusterId}/{database}/{tableName}'
  },

  // 测试数据
  testData: {
    cluster: {
      name: 'AutoTest-Cluster-' + Date.now(),
      description: '自动化测试集群',
      hive_metastore_url: 'mysql://testuser:testpass@localhost:3306/test_hive',
      hdfs_namenode_url: 'hdfs://localhost:9000',
      cluster_type: 'CDH'
    },

    task: {
      task_name: 'AutoTest-Task-' + Date.now(),
      table_name: 'test_table',
      database_name: 'test_db',
      merge_strategy: 'safe_merge',
      target_file_size: 134217728 // 128MB
    },

    form: {
      invalidEmails: ['invalid', 'test@', '@test.com', ''],
      validEmails: ['test@example.com', 'user@test.org'],
      invalidUrls: ['invalid', 'htp://test', ''],
      validUrls: ['mysql://user:pass@host:3306/db', 'hdfs://namenode:9000']
    }
  },

  // 选择器
  selectors: {
    // 通用元素
    button: 'button',
    input: 'input',
    dialog: '.el-dialog',
    loadingMask: '.el-loading-mask',
    notification: '.el-notification',
    messageBox: '.el-message-box',

    // 集群管理页面
    clusters: {
      addButton: 'button:has-text("添加集群")',
      clusterCard: '.cluster-card',
      editButton: 'button:has-text("编辑")',
      deleteButton: 'button:has-text("删除")',
      testButton: 'button:has-text("快速测试")',
      detailButton: '.cluster-actions button:first-child',
      dialog: '.el-dialog',
      nameInput: 'input[placeholder*="集群名称"]',
      descInput: 'textarea[placeholder*="描述"]',
      metastoreInput: 'input[placeholder*="MetaStore"]',
      hdfsInput: 'input[placeholder*="NameNode"]',
      saveButton: '.el-dialog .el-button--primary',
      cancelButton: '.el-dialog .el-button:has-text("取消")'
    },

    // 仪表板
    dashboard: {
      refreshButton: 'button:has-text("刷新")',
      exportButton: 'button:has-text("导出")',
      timeRange: '.time-range-selector',
      summaryCards: '.summary-card',
      charts: '.chart-container'
    },

    // 表管理
    tables: {
      scanButton: 'button:has-text("扫描")',
      filterInput: '.filter-input',
      tableRow: '.table-row',
      sortHeader: '.sort-header'
    },

    // 任务管理
    tasks: {
      createButton: 'button:has-text("创建任务")',
      executeButton: 'button:has-text("执行")',
      cancelButton: 'button:has-text("取消")',
      taskRow: '.task-row',
      statusFilter: '.status-filter'
    },

    // 设置页面
    settings: {
      saveButton: 'button:has-text("保存")',
      resetButton: 'button:has-text("重置")',
      refreshButton: 'button:has-text("刷新系统状态")',
      configForm: '.config-form'
    }
  },

  // 测试场景
  scenarios: {
    // 按钮功能测试场景
    buttonTests: [
      { page: 'clusters', buttons: ['addButton', 'editButton', 'testButton', 'detailButton'] },
      { page: 'dashboard', buttons: ['refreshButton', 'exportButton'] },
      { page: 'tables', buttons: ['scanButton'] },
      { page: 'tasks', buttons: ['createButton', 'executeButton'] },
      { page: 'settings', buttons: ['saveButton', 'resetButton', 'refreshButton'] }
    ],

    // 表单验证测试场景
    formTests: [
      {
        page: 'clusters',
        form: 'cluster',
        validationTests: [
          { field: 'name', empty: true, errorExpected: true },
          { field: 'hive_metastore_url', invalid: true, errorExpected: true },
          { field: 'hdfs_namenode_url', invalid: true, errorExpected: true }
        ]
      }
    ],

    // 导航测试场景
    navigationTests: [
      { from: 'clusters', to: 'dashboard' },
      { from: 'dashboard', to: 'tables' },
      { from: 'tables', to: 'tasks' },
      { from: 'tasks', to: 'settings' },
      { from: 'settings', to: 'clusters' }
    ],

    // API错误测试场景
    apiErrorTests: [
      { endpoint: '/api/v1/clusters/', method: 'GET', expectStatus: 200 },
      { endpoint: '/api/v1/tables/metrics', method: 'GET', expectStatus: 200 },
      { endpoint: '/api/v1/tasks/', method: 'GET', expectStatus: 200 },
      { endpoint: '/health', method: 'GET', expectStatus: 200 }
    ]
  },

  // 测试选项
  options: {
    headless: false, // 显示浏览器窗口用于调试
    slowMo: 100, // 操作间延迟100ms
    screenshot: true, // 错误时截图
    video: false, // 不录制视频
    viewport: { width: 1280, height: 720 },
    timeout: 10000 // 单个操作超时时间
  },

  // 报告配置
  reporting: {
    outputDir: './test-results',
    htmlReport: true,
    jsonReport: true,
    screenshots: true,
    detailedLogs: true
  }
}

module.exports = TEST_CONFIG
