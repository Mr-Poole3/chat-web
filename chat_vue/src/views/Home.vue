<template>
  <div class="container">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <div class="sidebar-header">
        天汇AI工具集
      </div>
      <div class="sidebar-tools">
        <div
          v-for="feature in features"
          :key="feature.id"
          @click="navigateToFeature(feature)"
          class="tool-item"
          :class="{ active: currentFeature === feature.id }"
        >
          <i :class="feature.icon"></i>
          <span>{{ feature.title }}</span>
        </div>

        <div v-if="userStore.isAuthenticated" @click="handleLogout" class="tool-item logout-item">
          <i class="fas fa-sign-out-alt"></i>
          <span>退出登录</span>
        </div>

        <div v-else @click="navigateToLogin" class="tool-item">
          <i class="fas fa-sign-in-alt"></i>
          <span>登录/注册</span>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <div class="welcome-section">
        <h1>欢迎使用 天汇AI 工具箱</h1>
        <p class="welcome-description">这是一个强大的 AI 工具合集，提供多种智能服务，包括 AI 聊天、PDF 转换、论文写作、简历生成等功能。</p>

        <div class="user-info" v-if="userStore.isAuthenticated">
          <div class="user-avatar">
            {{ userStore.user?.username?.charAt(0).toUpperCase() || 'U' }}
          </div>
          <div class="user-details">
            <div class="user-name">{{ userStore.user?.username || '用户' }}</div>
            <div class="user-status">已登录</div>
          </div>
        </div>

        <div class="features-grid">
          <div
            v-for="feature in features"
            :key="feature.id"
            class="feature-card"
            @click="navigateToFeature(feature)"
          >
            <div class="feature-icon">
              <i :class="feature.icon"></i>
            </div>
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.description }}</p>
          </div>
        </div>

        <div class="auth-buttons" v-if="!userStore.isAuthenticated">
          <router-link to="/login" class="auth-button login-button">
            <i class="fas fa-sign-in-alt"></i> 登录
          </router-link>
          <router-link to="/register" class="auth-button register-button">
            <i class="fas fa-user-plus"></i> 注册
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const currentFeature = ref(route.query.feature || 'chat')

const features = [
  {
    id: 'chat',
    icon: 'fas fa-robot',
    title: 'AI 聊天',
    description: '与智能 AI 助手进行自然对话，获取帮助和建议。'
  },
  {
    id: 'pdf',
    icon: 'fas fa-file-pdf',
    title: 'PDF 转换',
    description: '将 PDF 文件转换为其他格式，支持多种文档类型。'
  },
  {
    id: 'paper',
    icon: 'fas fa-pen-fancy',
    title: '论文写作',
    description: '智能辅助论文写作，提供写作建议和格式规范。'
  },
  {
    id: 'resume',
    icon: 'fas fa-file-alt',
    title: '简历生成',
    description: '一键生成专业简历。'
  }
]

const navigateToFeature = (feature) => {
  if (!userStore.isAuthenticated) {
    router.push('/login')
    return
  }
  router.push(`/chat?feature=${feature.id}`)
}

const navigateToLogin = () => {
  router.push('/login')
}

const handleLogout = () => {
  userStore.logout()
  console.log('用户已退出登录')
}
</script>

<style scoped>
/* 全局布局 */
.container {
  display: flex;
  height: 100vh;
  width: 100%;
  overflow: hidden;
}

/* 侧边栏样式 */
.sidebar {
  width: 260px;
  min-width: 260px;
  background-color: #161923;
  border-right: 1px solid rgba(99, 102, 241, 0.2);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding-bottom: 20px;
  box-shadow: 0 0 20px rgba(76, 78, 229, 0.1);
}

.sidebar-header {
  padding: 20px;
  text-align: center;
  font-size: 22px;
  font-weight: 600;
  border-bottom: 1px solid rgba(99, 102, 241, 0.2);
  background: linear-gradient(90deg, #4c4ed9, #6366f1);
  color: white;
  letter-spacing: 1px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.sidebar-tools {
  padding-top: 10px;
}

.tool-item {
  display: flex;
  align-items: center;
  padding: 15px 20px;
  color: #e0e0ff;
  text-decoration: none;
  border-bottom: 1px solid rgba(99, 102, 241, 0.2);
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.tool-item i {
  font-size: 20px;
  margin-right: 15px;
  color: #6366f1;
}

.tool-item span {
  font-size: 16px;
  font-weight: 500;
}

.tool-item:hover {
  background-color: rgba(99, 102, 241, 0.1);
  transform: translateX(5px);
}

.tool-item.active {
  background-color: rgba(99, 102, 241, 0.2);
  border-left: 4px solid #6366f1;
}

.tool-item:hover::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.1), transparent);
  animation: shine 1.5s infinite;
}

@keyframes shine {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.logout-item {
  margin-top: 20px;
  border-top: 1px solid rgba(99, 102, 241, 0.2);
}

.logout-item i {
  color: #ef4444;
}

/* 主内容区样式 */
.main-content {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #0f1117;
  background-image: radial-gradient(circle at 25% 25%, rgba(99, 102, 241, 0.05) 1%, transparent 10%),
                    radial-gradient(circle at 75% 75%, rgba(99, 102, 241, 0.05) 1%, transparent 10%);
  background-size: 60px 60px;
  overflow-y: auto;
  padding: 40px;
}

.welcome-section {
  max-width: 1000px;
  margin: 0 auto;
  padding: 40px;
  background: rgba(30, 33, 48, 0.7);
  border-radius: 16px;
  border: 1px solid rgba(99, 102, 241, 0.2);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(10px);
}

h1 {
  font-size: 36px;
  margin-bottom: 20px;
  text-align: center;
  background: linear-gradient(90deg, #4c4ed9, #6366f1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 700;
  letter-spacing: 1px;
}

.welcome-description {
  font-size: 18px;
  color: #a5b4fc;
  margin-bottom: 30px;
  line-height: 1.6;
  text-align: center;
}

.user-info {
  display: flex;
  align-items: center;
  padding: 15px 20px;
  margin: 20px 0;
  background: rgba(22, 25, 35, 0.7);
  border-radius: 10px;
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.user-avatar {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4c4ed9, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
  margin-right: 15px;
}

.user-details {
  flex: 1;
}

.user-name {
  font-size: 16px;
  font-weight: 600;
  color: #e0e0ff;
}

.user-status {
  font-size: 14px;
  color: #a5b4fc;
  margin-top: 4px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 25px;
  margin-top: 30px;
}

.feature-card {
  background: rgba(22, 25, 35, 0.7);
  padding: 25px;
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.2);
  transition: all 0.3s ease;
  cursor: pointer;
  text-align: center;
}

.feature-card:hover {
  transform: translateY(-10px);
  border-color: rgba(99, 102, 241, 0.6);
  box-shadow: 0 10px 25px rgba(99, 102, 241, 0.2);
}

.feature-icon {
  font-size: 36px;
  color: #6366f1;
  margin-bottom: 20px;
}

.feature-card h3 {
  font-size: 20px;
  color: #e0e0ff;
  margin: 0 0 15px;
}

.feature-card p {
  color: #a5b4fc;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}

.auth-buttons {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 40px;
}

.auth-button {
  padding: 12px 30px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.login-button {
  background: linear-gradient(90deg, #4c4ed9, #6366f1);
  color: white;
  border: none;
}

.register-button {
  background: transparent;
  color: #6366f1;
  border: 1px solid rgba(99, 102, 241, 0.4);
}

.auth-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}

.login-button:hover {
  background: linear-gradient(90deg, #3b3db3, #4f46e5);
}

.register-button:hover {
  background: rgba(99, 102, 241, 0.1);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .container {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    min-width: 0;
    height: auto;
    max-height: 300px;
  }

  .main-content {
    padding: 20px;
  }

  .welcome-section {
    padding: 20px;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }
}
</style>