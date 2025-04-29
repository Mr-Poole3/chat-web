import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue')
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/Chat.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/subscription',
    name: 'Subscription',
    component: () => import('@/views/Subscription.vue'),
    meta: { requiresAuth: true }
  },
  // 添加匹配所有未知路由的catch-all路由
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  console.log('路由守卫触发:', {
    to: to.path,
    from: from.path,
    requiresAuth: to.meta.requiresAuth,
    requiresAdmin: to.meta.requiresAdmin
  })

  const userStore = useUserStore()
  
  // 优先初始化用户状态
  if (userStore.token) {
    try {
      // 如果有token但没有user信息，先尝试初始化
      if (!userStore.user) {
        await userStore.init()
      }
      // 即使有user信息，也检查token是否有效
      else if (!userStore.isTokenValid) {
        console.log('令牌无效，执行登出')
        userStore.logout()
      }
    } catch (error) {
      console.error('初始化用户状态失败:', error)
    }
  }
  
  // 重新检查认证状态
  const isAuthenticated = userStore.isAuthenticated && userStore.isTokenValid
  const user = userStore.user

  console.log('当前认证状态:', {
    isAuthenticated,
    tokenValid: userStore.isTokenValid,
    user: user ? { id: user.id, username: user.username, role: user.role } : null
  })

  // 处理需要认证的路由
  if (to.meta.requiresAuth) {
    if (!isAuthenticated) {
      console.log('需要认证，但用户未登录或令牌无效，重定向到登录页')
      next({
        path: '/login',
        query: { redirect: to.fullPath !== '/' ? to.fullPath : undefined }
      })
      return
    }
    
    // 检查管理员权限
    if (to.meta.requiresAdmin && (!user || user.role !== 'admin')) {
      console.log('需要管理员权限，但用户不是管理员，重定向到首页')
      next('/')
      return
    }
  } else if (to.path === '/login' && isAuthenticated) {
    // 已登录用户尝试访问登录页，重定向到首页
    console.log('已登录用户尝试访问登录页，重定向到首页')
    next('/')
    return
  }

  next()
})

export default router