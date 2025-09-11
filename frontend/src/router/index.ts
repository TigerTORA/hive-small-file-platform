import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      redirect: '/clusters'
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
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: '监控仪表板' }
    },
    {
      path: '/tables',
      name: 'Tables',
      component: () => import('@/views/Tables.vue'),
      meta: { title: '表管理' }
    },
    {
      path: '/tables/:clusterId/:database/:tableName',
      name: 'TableDetail',
      component: () => import('@/views/TableDetail.vue'),
      meta: { title: '表详情' },
      props: true
    },
    {
      path: '/tasks',
      name: 'Tasks',
      component: () => import('@/views/Tasks.vue'),
      meta: { title: '任务管理' }
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/Settings.vue'),
      meta: { title: '系统设置' }
    },
    {
      path: '/test-dashboard',
      name: 'TestDashboard',
      component: () => import('@/views/TestDashboard.vue'),
      meta: { title: '测试中心' }
    }
  ]
})

// 设置页面标题
router.beforeEach((to, from, next) => {
  if (to.meta?.title) {
    document.title = `${to.meta.title} - Hive 小文件治理平台`
  }
  next()
})

export default router