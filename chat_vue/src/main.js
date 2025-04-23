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
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      router.push('/login')
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
app.use(Toast, toastOptions)
app.component('DotLottieVue', DotLottieVue)

app.mount('#app')