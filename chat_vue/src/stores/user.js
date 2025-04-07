import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const isAuthenticated = computed(() => {
    return !!token.value
  })

  const login = async (credentials) => {
    try {
      const formData = new URLSearchParams()
      formData.append('username', credentials.username)
      formData.append('password', credentials.password)

      console.log('Attempting login with:', credentials.username)
      const response = await axios.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      })

      console.log('Login successful, got token:', response.data.access_token)
      token.value = response.data.access_token
      localStorage.setItem('token', token.value)
      await fetchUserInfo()

      // 不再在这里处理路由跳转，由登录组件处理
      // router.push('/chat')
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }

  const register = async (username, email, password) => {
    try {
      console.log('Attempting registration for:', username)
      const response = await axios.post('/auth/register', {
        username,
        email,
        password
      })

      console.log('Registration successful:', response.data)
      return response.data
    } catch (error) {
      console.error('Registration failed:', error)
      throw error
    }
  }

  const logout = () => {
    // 直接清除本地存储的token，不调用后端接口
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    console.log('User logged out, token cleared')
    router.push('/login')
  }

  const fetchUserInfo = async () => {
    try {
      const response = await axios.get('/auth/me', {
        headers: {
          'Authorization': `Bearer ${token.value}`
        }
      })
      user.value = response.data
    } catch (error) {
      console.error('Failed to fetch user info:', error)
      throw error
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    register,
    logout,
    fetchUserInfo
  }
})