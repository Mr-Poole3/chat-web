import { defineStore } from 'pinia'
import axios from 'axios'
import router from '@/router'
import { jwtDecode } from 'jwt-decode'

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null,
    isAuthenticated: false,
    token: localStorage.getItem('token') || null
  }),

  getters: {
    userId: (state) => state.user?.id || null,
    username: (state) => state.user?.username || null,
    role: (state) => state.user?.role || 'user',
    isAdmin: (state) => state.user?.role === 'admin',
    
    // 检查令牌是否有效
    isTokenValid() {
      if (!this.token) return false
      
      try {
        const decoded = jwtDecode(this.token)
        const currentTime = Date.now() / 1000
        
        // 检查令牌是否过期
        if (decoded.exp && decoded.exp < currentTime) {
          console.log('令牌已过期')
          return false
        }
        
        return true
      } catch (error) {
        console.error('解析令牌出错:', error)
        return false
      }
    }
  },

  actions: {
    // 初始化用户状态
    async init() {
      if (this.token) {
        // 有令牌但没有用户信息，尝试获取用户信息
        if (this.isTokenValid()) {
          try {
            await this.fetchUserInfo()
            return true
          } catch (error) {
            console.error('初始化用户状态失败:', error)
            // 仅当API明确返回401时才登出
            if (error.response && error.response.status === 401) {
              this.logout()
            }
            return false
          }
        } else {
          // 令牌无效，执行登出
          console.log('令牌无效，执行登出')
          this.logout()
          return false
        }
      }
      return false
    },
    
    // 检查令牌有效性但不主动登出，用于页面刷新时状态检查
    checkTokenValidity() {
      if (!this.token) return false
      return this.isTokenValid()
    },
    
    async login(credentials) {
      try {
        console.log('开始登录流程，用户名:', credentials.username)
        
        // 修正：确保使用正确的数据格式，将对象解构为表单格式
        const formData = new URLSearchParams()
        formData.append('username', credentials.username)
        formData.append('password', credentials.password)
        
        const response = await axios.post('/auth/login', formData, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        })
        
        console.log('登录响应:', response.data)
        
        const { access_token } = response.data
        this.token = access_token
        this.isAuthenticated = true
        localStorage.setItem('token', access_token)
        
        // 获取用户信息
        await this.fetchUserInfo()
        console.log('登录成功，用户信息:', this.user)
        return true
      } catch (error) {
        console.error('登录失败:', error)
        this.logout()
        throw error
      }
    },

    async fetchUserInfo() {
      try {
        console.log('开始获取用户信息')
        const response = await axios.get('/auth/me', {
          headers: {
            Authorization: `Bearer ${this.token}`
          }
        })
        console.log('获取用户信息成功:', response.data)
        this.user = response.data
        this.isAuthenticated = true
        return this.user
      } catch (error) {
        console.error('获取用户信息失败:', error)
        this.logout()
        throw error
      }
    },

    logout() {
      console.log('执行登出操作')
      this.user = null
      this.isAuthenticated = false
      this.token = null
      localStorage.removeItem('token')
      
      // 判断当前路由是否需要登录，如果需要，则跳转到登录页
      const currentRoute = router.currentRoute.value
      if (currentRoute.meta.requiresAuth) {
        router.push({
          path: '/login',
          query: { redirect: currentRoute.fullPath }
        })
      }
      
      console.log('登出完成')
    },

    async register(username, email, password) {
      try {
        console.log('开始注册流程，用户名:', username)
        const response = await axios.post('/auth/register', {
          username,
          email,
          password
        })
        console.log('注册成功:', response.data)
        return response.data
      } catch (error) {
        console.error('注册失败:', error)
        throw error
      }
    },

    async forgotPassword(username, email, newPassword) {
      try {
        console.log('开始重置密码流程，用户名:', username)
        const response = await axios.post('/auth/reset-password', {
          username,
          email,
          new_password: newPassword
        })
        console.log('密码重置成功:', response.data)
        return response.data
      } catch (error) {
        console.error('密码重置失败:', error)
        throw error
      }
    },

    setToken(newToken) {
      console.log('设置新token')
      this.token = newToken
      localStorage.setItem('token', newToken)
    },

    clearToken() {
      console.log('清除token')
      this.token = null
      localStorage.removeItem('token')
    },

    setUsername(newUsername) {
      if (this.user) {
        console.log('更新用户名:', newUsername)
        this.user.username = newUsername
      }
    },

    setUserId(newUserId) {
      if (this.user) {
        console.log('更新用户ID:', newUserId)
        this.user.id = newUserId
      }
    }
  }
})