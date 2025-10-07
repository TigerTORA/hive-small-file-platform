import { createRouter, createWebHashHistory } from 'vue-router'
import { useMonitoringStore } from '@/stores/monitoring'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: '监控中心', requiresCluster: true }
    },
    {
      path: '/clusters',
      name: 'ClustersManagement',
      component: () => import('@/views/ClustersManagement.vue'),
      meta: { title: '集群管理' }
    },
    {
      path: '/clusters/:id',
      name: 'ClusterDetail',
      component: () => import('@/views/ClusterDetail.vue'),
      meta: { title: '集群详情' },
      props: true
    },
    {
      path: '/tables',
      name: 'Tables',
      component: () => import('@/views/Tables.vue'),
      meta: { title: '表管理', requiresCluster: true }
    },
    {
      path: '/tables/:clusterId/:database/:tableName',
      name: 'TableDetail',
      component: () => import('@/views/TableDetail.vue'),
      meta: { title: '表详情', requiresCluster: true },
      props: true
    },
    {
      path: '/tasks',
      name: 'Tasks',
      component: () => import('@/views/Tasks.vue'),
      meta: { title: '任务管理' }
    },
    {
      path: '/governance-flow',
      name: 'GovernanceFlow',
      component: () => import('@/views/GovernanceFlow.vue'),
      meta: { title: '治理流程' }
    },
    {
      path: '/partition-archive',
      name: 'PartitionArchive',
      component: () => import('@/views/PartitionArchive.vue'),
      meta: { title: '分区归档管理', requiresCluster: true }
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/Settings.vue'),
      meta: { title: '系统设置' }
    },
    {
      path: '/big-screen',
      name: 'BigScreen',
      component: () => import('@/views/BigScreen.vue'),
      meta: { title: '实时监控大屏', fullscreen: true }
    },
    {
      path: '/test-table-generator',
      name: 'TestTableGenerator',
      component: () => import('@/views/TestTableGenerator.vue'),
      meta: { title: '测试表生成器', requiresCluster: true }
    }
  ]
})

// 路由守卫：检查集群选择和设置页面标题
router.beforeEach((to, from, next) => {
  // 若访问根路径且尚未选择集群，统一跳转到集群管理
  try {
    const monitoringStore = useMonitoringStore()
    const hasCluster = !!monitoringStore.settings.selectedCluster
    if (to.path === '/' && !hasCluster) {
      next('/clusters')
      return
    }
  } catch {}

  // 设置页面标题
  if (to.meta?.title) {
    document.title = `${to.meta.title} - DataNova`
  }

  // 检查是否需要集群权限
  if (to.meta?.requiresCluster) {
    const monitoringStore = useMonitoringStore()
    const hasCluster = !!monitoringStore.settings.selectedCluster
    // 如果没有选择集群，重定向到集群管理页面
    if (!hasCluster) {
      const targetPath = encodeURIComponent(to.fullPath)
      next(`/clusters?redirect=${targetPath}`)
      return
    }
  }

  next()
})

export default router
