import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import Home from '@/views/Home.vue'
import Chat from '@/views/Chat.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home,
      meta: { requiresAuth: true }  // 主页也需要认证
    },
    {
      path: '/chat',
      name: 'chat',
      component: Chat,
      meta: { requiresAuth: true }
    },
    {
      path: '/subscription',
      name: 'subscription',
      component: () => import('@/views/Subscription.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresGuest: true }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/Register.vue'),
      meta: { requiresGuest: true }
    }
  ]
})

// 导航守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const isAuthenticated = userStore.isAuthenticated || !!localStorage.getItem('token')


  // 需要认证的路由
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!isAuthenticated) {
      next({
        name: 'login',
        query: { redirect: to.fullPath }  // 保存原目标路径
      })
    } else {
      next()
    }
  }
  // 游客路由（登录/注册）
  else if (to.matched.some(record => record.meta.requiresGuest)) {
    if (isAuthenticated) {
      next({ name: 'home' })  // 已登录用户重定向到 home 页面
    } else {
      next()
    }
  }
  else {
    next()
  }
})

export default router