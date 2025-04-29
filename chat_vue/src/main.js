import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import axios from 'axios'
import { DotLottieVue } from '@lottiefiles/dotlottie-vue'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'

// 使用环境变量配置API基础URL
axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
axios.defaults.headers.common['Content-Type'] = 'application/json'
axios.defaults.withCredentials = false

// 添加请求拦截器
axios.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 添加响应拦截器
axios.interceptors.response.use(
  response => response,
  error => {
    // 处理 401 未授权错误（令牌过期或无效）
    if (error.response && error.response.status === 401) {
      console.log('令牌已过期或无效，重定向到登录页面')
      
      // 清除本地存储的令牌和用户信息
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      
      // 如果存在 Pinia 存储，也清除该状态
      const pinia = router.app?._instance?.appContext.app.config.globalProperties.$pinia
      if (pinia) {
        const userStore = pinia._s.get('user')
        if (userStore) {
          userStore.logout()
        }
      }
      
      // 重定向到登录页面，但避免循环
      const currentPath = router.currentRoute.value.fullPath
      if (currentPath !== '/login' && !currentPath.startsWith('/login')) {
        router.push({
          path: '/login',
          query: { redirect: currentPath !== '/' ? currentPath : undefined }
        })
      }
    }
    return Promise.reject(error)
  }
)

// 导入 Font Awesome
import '@fortawesome/fontawesome-free/css/all.min.css'

const app = createApp(App)

// Toast 配置
const toastOptions = {
  position: 'top-right',
  timeout: 3000,
  closeOnClick: true,
  pauseOnFocusLoss: true,
  pauseOnHover: true,
  draggable: true,
  draggablePercent: 0.6,
  showCloseButtonOnHover: false,
  hideProgressBar: false,
  closeButton: 'button',
  icon: true,
  rtl: false,
  transition: 'Vue-Toastification__bounce',
  maxToasts: 5,
  newestOnTop: true
}

app.use(createPinia())
app.use(router)
app.use(DotLottieVue)
app.use(Toast, toastOptions)

app.mount('#app')