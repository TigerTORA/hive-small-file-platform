import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: '监控仪表板' }
    },
    {
      path: '/clusters',
      name: 'Clusters',
      component: () => import('@/views/Clusters.vue'),
      meta: { title: '集群管理' }
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