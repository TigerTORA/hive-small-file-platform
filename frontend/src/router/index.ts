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
      meta: { title: '任务管理', requiresCluster: true }
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
    }
  ]
})

// 路由守卫：检查集群选择和设置页面标题
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta?.title) {
    document.title = `${to.meta.title} - DataNova`
  }

  // 检查是否需要集群权限
  if (to.meta?.requiresCluster) {
    const monitoringStore = useMonitoringStore()

    // 如果没有选择集群，重定向到集群管理页面
    if (!monitoringStore.hasSelectedCluster) {
      const targetPath = encodeURIComponent(to.fullPath)
      next(`/clusters?redirect=${targetPath}`)
      return
    }
  }

  next()
})

export default router
