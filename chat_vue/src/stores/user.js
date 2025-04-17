import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref('')
  const userId = ref(null)
  const user = ref(null)

  const isAuthenticated = computed(() => {
    return !!token.value
  })

  const login = async (credentials) => {
    try {
      const formData = new URLSearchParams()
      formData.append('username', credentials.username)
      formData.append('password', credentials.password)

      const response = await axios.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      })

      token.value = response.data.access_token
      localStorage.setItem('token', token.value)
      await fetchUserInfo()
    } catch (error) {
      throw error
    }
  }

  const register = async (username, email, password) => {
    try {
      const response = await axios.post('/auth/register', {
        username,
        email,
        password
      })

      return response.data
    } catch (error) {
      throw error
    }
  }

  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
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
      throw error
    }
  }

  function setToken(newToken) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }
  
  function clearToken() {
    token.value = ''
    localStorage.removeItem('token')
  }
  
  function setUsername(newUsername) {
    username.value = newUsername
  }
  
  function setUserId(newUserId) {
    userId.value = newUserId
  }

  return {
    token,
    username,
    userId,
    user,
    isAuthenticated,
    login,
    register,
    logout,
    fetchUserInfo,
    setToken,
    clearToken,
    setUsername,
    setUserId
  }
})