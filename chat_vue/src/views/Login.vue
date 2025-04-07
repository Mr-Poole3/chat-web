<template>
  <div class="login-container">
    <div class="login-form-wrapper">
      <div class="login-header">
        <h1>登录</h1>
      </div>
      <form @submit.prevent="handleSubmit" class="login-form">
        <div class="form-group" :class="{ error: errors.username }">
          <label for="username">用户名</label>
          <input
            v-model="form.username"
            type="text"
            id="username"
            required
            @input="clearError('username')"
          >
          <div v-if="errors.username" class="error-message">{{ errors.username }}</div>
        </div>
        <div class="form-group" :class="{ error: errors.password }">
          <label for="password">密码</label>
          <input
            v-model="form.password"
            type="password"
            id="password"
            required
            @input="clearError('password')"
          >
          <div v-if="errors.password" class="error-message">{{ errors.password }}</div>
        </div>
        <div v-if="error" class="error-message general-error">
          {{ error }}
        </div>
        <button type="submit" class="login-button" :disabled="loading">
          <span v-if="!loading">登录</span>
          <div v-else class="loading-spinner"></div>
        </button>
      </form>
      <div class="register-link">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const form = ref({
  username: '',
  password: ''
})

const loading = ref(false)
const error = ref('')

const errors = reactive({
  username: '',
  password: '',
  general: ''
})

const clearError = (field) => {
  errors[field] = ''
  errors.general = ''
}

const handleSubmit = async () => {
  if (!form.value.username || !form.value.password) {
    error.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  error.value = ''

  try {
    await userStore.login({
      username: form.value.username,
      password: form.value.password
    })

    // 如果有重定向参数则使用它，否则跳转到 chat 页面
    const redirectPath = route.query.redirect || '/chat'
    console.log('Login successful, redirecting to:', redirectPath)
    router.push(redirectPath)
  } catch (err) {
    error.value = err.response?.data?.detail || '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 20px;
  background-color: #0f1117;
}

.login-form-wrapper {
  background-color: rgba(30, 33, 48, 0.7);
  border-radius: 10px;
  padding: 40px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  backdrop-filter: blur(10px);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h1 {
  font-size: 24px;
  margin: 0;
  background: linear-gradient(90deg, #4c4ed9, #6366f1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 1px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #a5b4fc;
  font-size: 14px;
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 1px solid rgba(99, 102, 241, 0.4);
  border-radius: 6px;
  background-color: rgba(22, 25, 35, 0.7);
  color: #e0e0ff;
  font-size: 16px;
  transition: all 0.3s ease;
}

.form-group input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.3);
}

.form-group.error input {
  border-color: #ef4444;
}

.form-group.error label {
  color: #ef4444;
}

.error-message {
  color: #ef4444;
  font-size: 14px;
  margin-top: 5px;
  display: none;
}

.form-group.error .error-message {
  display: block;
}

.general-error {
  display: block;
  margin-bottom: 20px;
  padding: 8px;
  background-color: rgba(239, 68, 68, 0.1);
  border-radius: 4px;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.login-button {
  width: 100%;
  padding: 12px;
  background: linear-gradient(90deg, #4c4ed9, #6366f1);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.login-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(99, 102, 241, 0.3);
}

.login-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid #fff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.register-link {
  text-align: center;
  margin-top: 20px;
  color: #a5b4fc;
}

.register-link a {
  color: #6366f1;
  text-decoration: none;
  font-weight: 500;
}

.register-link a:hover {
  text-decoration: underline;
}
</style>