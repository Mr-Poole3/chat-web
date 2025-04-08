import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import axios from 'axios'
import { DotLottieVue } from '@lottiefiles/dotlottie-vue'

// 设置 axios 默认配置
axios.defaults.baseURL = '/api/v1'
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

app.use(createPinia())
app.use(router)
app.component('DotLottieVue', DotLottieVue)

app.mount('#app')