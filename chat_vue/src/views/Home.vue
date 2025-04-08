<template>
  <div class="container">
    <!-- 移动端菜单按钮 -->
    <div class="mobile-menu-toggle" @click="toggleSidebar">
      <i class="fas fa-bars"></i>
    </div>
    
    <!-- 侧边栏遮罩 -->
    <div class="sidebar-overlay" :class="{ active: sidebarVisible }" @click="toggleSidebar"></div>
    
    <!-- 侧边栏 -->
    <div class="sidebar" :class="{ visible: sidebarVisible }">
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
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const currentFeature = ref(route.query.feature || 'chat')
const sidebarVisible = ref(false)

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
  if (window.innerWidth <= 768) {
    sidebarVisible.value = false // 在移动端点击后关闭侧边栏
  }
}

const navigateToLogin = () => {
  router.push('/login')
}

const handleLogout = () => {
  userStore.logout()
  console.log('用户已退出登录')
}

const toggleSidebar = () => {
  sidebarVisible.value = !sidebarVisible.value
}

// 在窗口大小变化时处理侧边栏显示状态
const handleResize = () => {
  if (window.innerWidth > 768) {
    sidebarVisible.value = false
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  handleResize() // 初始调用一次
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
/* 全局布局 */
.container {
  display: flex;
  height: 100vh;
  width: 100%;
  overflow: hidden;
  position: relative;
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
  z-index: 100;
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
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(5px);
  border: 1px solid rgba(99, 102, 241, 0.3);
}

.welcome-section h1 {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 20px;
  background: linear-gradient(90deg, #4c4ed9, #6366f1);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  text-align: center;
}

.welcome-description {
  color: #a5b4fc;
  text-align: center;
  margin-bottom: 30px;
  font-size: 18px;
  line-height: 1.6;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
  margin: 30px 0;
}

.feature-card {
  background: rgba(22, 25, 35, 0.8);
  border-radius: 12px;
  padding: 25px;
  border: 1px solid rgba(99, 102, 241, 0.2);
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 25px rgba(99, 102, 241, 0.2);
  border-color: rgba(99, 102, 241, 0.5);
}

.feature-card:hover::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(225deg, transparent, rgba(99, 102, 241, 0.1), transparent);
  animation: shine 2s infinite;
}

.feature-icon {
  background: linear-gradient(135deg, #4c4ed9, #6366f1);
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  box-shadow: 0 4px 10px rgba(99, 102, 241, 0.3);
  transition: all 0.3s ease;
}

.feature-card:hover .feature-icon {
  transform: scale(1.1) rotate(5deg);
}

.feature-icon i {
  font-size: 28px;
  color: white;
}

.feature-card h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #e0e0ff;
}

.feature-card p {
  color: #a5b4fc;
  font-size: 14px;
  line-height: 1.5;
}

.user-info {
  display: flex;
  align-items: center;
  padding: 15px 20px;
  background: rgba(22, 25, 35, 0.8);
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.2);
  margin-bottom: 30px;
}

.user-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4c4ed9, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
  color: white;
  margin-right: 15px;
  box-shadow: 0 4px 10px rgba(99, 102, 241, 0.3);
}

.user-details {
  flex: 1;
}

.user-name {
  font-size: 18px;
  font-weight: 600;
  color: #e0e0ff;
  margin-bottom: 5px;
}

.user-status {
  font-size: 14px;
  color: #10b981;
  display: flex;
  align-items: center;
}

.user-status::before {
  content: '';
  display: inline-block;
  width: 8px;
  height: 8px;
  background-color: #10b981;
  border-radius: 50%;
  margin-right: 6px;
}

.auth-buttons {
  display: flex;
  gap: 15px;
  margin-top: 20px;
  justify-content: center;
}

.auth-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 30px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.3s ease;
}

.login-button {
  background: linear-gradient(90deg, #4c4ed9, #6366f1);
  color: white;
  border: none;
}

.register-button {
  background: transparent;
  border: 1px solid rgba(99, 102, 241, 0.5);
  color: #a5b4fc;
}

.login-button:hover, .register-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}

/* 移动端菜单按钮 */
.mobile-menu-toggle {
  display: none;
  position: fixed;
  top: 15px;
  left: 15px;
  z-index: 150;
  width: 40px;
  height: 40px;
  background: rgba(30, 33, 48, 0.8);
  border-radius: 8px;
  border: 1px solid rgba(99, 102, 241, 0.3);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  align-items: center;
  justify-content: center;
  cursor: pointer;
  backdrop-filter: blur(5px);
  color: #6366f1;
  font-size: 20px;
}

/* 侧边栏遮罩 */
.sidebar-overlay {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 90;
  backdrop-filter: blur(3px);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .container {
    flex-direction: column;
  }
  
  .mobile-menu-toggle {
    display: flex;
  }
  
  .sidebar {
    position: fixed;
    left: -260px;
    top: 0;
    height: 100%;
    transition: left 0.3s ease;
  }
  
  .sidebar.visible {
    left: 0;
  }
  
  .sidebar-overlay.active {
    display: block;
  }
  
  .main-content {
    padding: 20px;
    width: 100%;
    margin-left: 0;
  }
  
  .welcome-section {
    padding: 20px;
  }
  
  .welcome-section h1 {
    font-size: 28px;
  }
  
  .welcome-description {
    font-size: 16px;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
    gap: 15px;
  }
  
  .user-info {
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 15px;
  }
  
  .user-avatar {
    margin-right: 0;
    margin-bottom: 10px;
  }
  
  .auth-buttons {
    flex-direction: column;
  }
}

/* 中等尺寸屏幕 */
@media (min-width: 769px) and (max-width: 1024px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .welcome-section {
    padding: 30px;
  }
}
</style>