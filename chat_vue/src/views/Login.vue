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
      <div class="forgot-password-link">
        <a href="#" @click.prevent="showForgotPasswordModal">忘记密码？</a>
      </div>
    </div>
  </div>

  <!-- 忘记密码模态框 -->
  <div v-if="isForgotPasswordModalVisible" class="modal">
    <div class="modal-content">
      <span class="close" @click="closeForgotPasswordModal">&times;</span>
      <h2 class="modal-title">重置密码</h2>
      <form @submit.prevent="handleForgotPassword" class="forgot-password-form">
        <div class="form-group" :class="{ error: errors.username }">
          <label for="forgot-username">用户名</label>
          <input
            v-model="forgotPasswordForm.username"
            type="text"
            id="forgot-username"
            required
            @input="clearError('username')"
          >
          <div v-if="errors.username" class="error-message">{{ errors.username }}</div>
        </div>
        <div class="form-group" :class="{ error: errors.email }">
          <label for="forgot-email">电子邮箱</label>
          <input
            v-model="forgotPasswordForm.email"
            type="email"
            id="forgot-email"
            required
            @input="clearError('email')"
          >
          <div v-if="errors.email" class="error-message">{{ errors.email }}</div>
        </div>
        <div class="form-group" :class="{ error: errors.newPassword }">
          <label for="new-password">新密码</label>
          <input
            v-model="forgotPasswordForm.newPassword"
            type="password"
            id="new-password"
            required
            @input="clearError('newPassword')"
          >
          <div class="password-requirements">
            密码必须包含至少8个字符，包括大小写字母和数字
          </div>
          <div v-if="errors.newPassword" class="error-message">{{ errors.newPassword }}</div>
        </div>
        <div v-if="error" class="error-message general-error">
          {{ error }}
        </div>
        <button type="submit" class="submit-button" :disabled="loading">
          <span v-if="!loading">重置密码</span>
          <div v-else class="loading-spinner"></div>
        </button>
      </form>
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

const forgotPasswordForm = reactive({
  username: '',
  email: '',
  newPassword: ''
})

const loading = ref(false)
const error = ref('')
const isForgotPasswordModalVisible = ref(false)

const errors = reactive({
  username: '',
  password: '',
  email: '',
  newPassword: '',
  general: ''
})

const clearError = (field) => {
  errors[field] = ''
  errors.general = ''
}

const showForgotPasswordModal = () => {
  isForgotPasswordModalVisible.value = true
}

const closeForgotPasswordModal = () => {
  isForgotPasswordModalVisible.value = false
  forgotPasswordForm.username = ''
  forgotPasswordForm.email = ''
  forgotPasswordForm.newPassword = ''
  error.value = ''
  Object.keys(errors).forEach(key => errors[key] = '')
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

const handleForgotPassword = async () => {
  if (!forgotPasswordForm.username || !forgotPasswordForm.email || !forgotPasswordForm.newPassword) {
    error.value = '请填写所有必填字段'
    return
  }

  // 验证密码
  const passwordError = validatePassword(forgotPasswordForm.newPassword)
  if (passwordError) {
    errors.newPassword = passwordError
    return
  }

  loading.value = true
  error.value = ''

  try {
    await userStore.forgotPassword(
      forgotPasswordForm.username,
      forgotPasswordForm.email,
      forgotPasswordForm.newPassword
    )
    closeForgotPasswordModal()
    alert('密码重置成功，请使用新密码登录')
    router.push('/login')
  } catch (err) {
    error.value = err.response?.data?.detail || '重置密码失败，请稍后重试'
  } finally {
    loading.value = false
  }
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
  background-clip: text;
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

.forgot-password-link {
  text-align: center;
  margin-top: 10px;
  color: #a5b4fc;
}

.forgot-password-link a {
  color: #6366f1;
  text-decoration: none;
  font-weight: 500;
}

.forgot-password-link a:hover {
  text-decoration: underline;
}

.modal {
  display: flex;
  justify-content: center;
  align-items: center;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  z-index: 200;
}

.modal-content {
  background-color: #1e2130;
  padding: 30px;
  border-radius: 10px;
  width: 400px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  color: #e0e0ff;
}

.modal-title {
  text-align: center;
  margin-bottom: 20px;
  font-size: 24px;
}

.close {
  color: #aaa;
  float: right;
  font-size: 28px;
  font-weight: bold;
  cursor: pointer;
}

.close:hover,
.close:focus {
  color: white;
  text-decoration: none;
  cursor: pointer;
}

.forgot-password-form {
  display: flex;
  flex-direction: column;
}

.submit-button {
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
  margin-top: 20px;
}

.submit-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(99, 102, 241, 0.3);
}

.submit-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.password-requirements {
  font-size: 12px;
  color: #a5b4fc;
  margin-top: 5px;
  margin-bottom: 5px;
}

/* 移动端适配 */
@media (max-width: 480px) {
  .login-form-wrapper {
    padding: 30px 20px;
    border-radius: 8px;
  }
  
  .login-header h1 {
    font-size: 22px;
  }
  
  .form-group label {
    font-size: 13px;
  }
  
  .form-group input {
    padding: 10px;
    font-size: 14px;
  }
  
  .login-button {
    padding: 10px;
    font-size: 15px;
  }
  
  .error-message {
    font-size: 13px;
  }
}
</style>