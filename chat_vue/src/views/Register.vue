<template>
  <div class="register-container">
    <div class="register-form-wrapper">
      <div class="register-header">
        <h1>注册</h1>
      </div>
      <form @submit.prevent="handleRegister" class="register-form">
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
        <div class="form-group" :class="{ error: errors.email }">
          <label for="email">电子邮箱</label>
          <input
            v-model="form.email"
            type="email"
            id="email"
            required
            @input="clearError('email')"
          >
          <div v-if="errors.email" class="error-message">{{ errors.email }}</div>
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
          <div class="password-requirements">
            密码必须包含至少8个字符，包括大小写字母和数字
          </div>
          <div v-if="errors.password" class="error-message">{{ errors.password }}</div>
        </div>
        <div class="form-group" :class="{ error: errors.confirmPassword }">
          <label for="confirm-password">确认密码</label>
          <input
            v-model="form.confirmPassword"
            type="password"
            id="confirm-password"
            required
            @input="clearError('confirmPassword')"
          >
          <div v-if="errors.confirmPassword" class="error-message">{{ errors.confirmPassword }}</div>
        </div>
        <div v-if="errors.general" class="error-message general-error">
          {{ errors.general }}
        </div>
        <button type="submit" class="register-button" :disabled="loading">
          <span v-if="!loading">注册</span>
          <div v-else class="loading-spinner"></div>
        </button>
      </form>
      <div class="login-link">
        已有账号？<router-link to="/login">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const errors = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  general: ''
})

const loading = ref(false)

const clearError = (field) => {
  errors[field] = ''
  errors.general = ''
}

const validatePassword = (password) => {
  if (password.length < 8) {
    return '密码长度必须至少为8个字符'
  }
  if (!/[A-Z]/.test(password)) {
    return '密码必须包含至少一个大写字母'
  }
  if (!/[a-z]/.test(password)) {
    return '密码必须包含至少一个小写字母'
  }
  if (!/[0-9]/.test(password)) {
    return '密码必须包含至少一个数字'
  }
  return ''
}

const handleRegister = async () => {
  loading.value = true
  try {
    // 验证密码
    const passwordError = validatePassword(form.password)
    if (passwordError) {
      errors.password = passwordError
      return
    }

    // 验证确认密码
    if (form.password !== form.confirmPassword) {
      errors.confirmPassword = '两次输入的密码不一致'
      return
    }

    await userStore.register(form.username, form.email, form.password)
    router.push('/login')
  } catch (error) {
    const errorMessage = error.response?.data?.detail || '注册失败，请稍后重试'
    if (errorMessage.toLowerCase().includes('username')) {
      errors.username = errorMessage
    } else if (errorMessage.toLowerCase().includes('email')) {
      errors.email = errorMessage
    } else if (errorMessage.toLowerCase().includes('password')) {
      errors.password = errorMessage
    } else {
      errors.general = errorMessage
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 20px;
  background-color: #0f1117;
}

.register-form-wrapper {
  background-color: rgba(30, 33, 48, 0.7);
  border-radius: 10px;
  padding: 40px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  backdrop-filter: blur(10px);
}

.register-header {
  text-align: center;
  margin-bottom: 30px;
}

.register-header h1 {
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

.password-requirements {
  font-size: 12px;
  color: #a5b4fc;
  margin-top: 5px;
}

.register-button {
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

.register-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(99, 102, 241, 0.3);
}

.register-button:disabled {
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

.login-link {
  text-align: center;
  margin-top: 20px;
  color: #a5b4fc;
}

.login-link a {
  color: #6366f1;
  text-decoration: none;
  font-weight: 500;
}

.login-link a:hover {
  text-decoration: underline;
}
</style>