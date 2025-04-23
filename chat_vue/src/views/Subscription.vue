<template>
  <div class="subscription-container">
    <div class="subscription-content">
      <div class="header-actions">
        <button class="back-button" @click="goBack">
          <i class="fas fa-arrow-left"></i>
          返回聊天
        </button>
      </div>
      
      <div class="subscription-status" v-if="subscriptionInfo">
        <div class="status-card">
          <div class="status-header">
            <i class="fas fa-crown"></i>
            <h2>当前订阅状态</h2>
          </div>
          <div class="status-content">
            <p class="status-text">订阅类型：{{ subscriptionInfo.is_vip ? 'VIP会员' : '免费用户' }}</p>
            <p class="status-text" v-if="subscriptionInfo.expire_time">
              到期时间：{{ formatDate(subscriptionInfo.expire_time) }}
            </p>
          </div>
        </div>
      </div>

      <div class="plans-container">
        <div class="plan-card" v-for="plan in plans" :key="plan.id">
          <div class="plan-header">
            <h3>{{ plan.name }}</h3>
            <div class="plan-price">
              <span class="price">¥{{ plan.price }}</span>
              <span class="period">/{{ plan.period }}</span>
            </div>
          </div>
          
          <div class="plan-features">
            <ul>
              <li v-for="feature in plan.features" :key="feature">
                <i class="fas fa-check"></i>
                {{ feature }}
              </li>
            </ul>
          </div>
          
          <button 
            class="subscribe-button"
            :class="{ 'current-plan': plan.id === currentPlanId }"
            @click="handleSubscribe(plan)"
          >
            {{ plan.id === currentPlanId ? '当前计划' : '立即订阅' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const userId = ref(userStore.userId)
const subscriptionInfo = ref(null)
const plans = ref([
  {
    id: 'weekly',
    name: '周卡会员',
    price: '9.9',
    period: '周',
    features: [
      '无限次使用所有AI模型',
      '优先响应',
      '更长的上下文记忆',
      '专属客服支持'
    ]
  },
  {
    id: 'monthly',
    name: '月度会员',
    price: '29.9',
    period: '月',
    features: [
      '无限次使用所有AI模型',
      '优先响应',
      '更长的上下文记忆',
      '专属客服支持',
      '节省30%费用'
    ]
  },
  {
    id: 'yearly',
    name: '年度会员',
    price: '299',
    period: '年',
    features: [
      '无限次使用所有AI模型',
      '优先响应',
      '更长的上下文记忆',
      '专属客服支持',
      '节省50%费用'
    ]
  }
])
const currentPlanId = ref(null)

const goBack = () => {
  router.push('/chat')
}

const fetchSubscriptionInfo = async () => {
  try {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/login')
      return
    }

    const response = await axios.get('/user/subscription', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })

    if (response.data.code === 200) {
      subscriptionInfo.value = response.data.data
      currentPlanId.value = subscriptionInfo.value.is_vip ? 'yearly' : null
    }
  } catch (error) {
    console.error('获取订阅信息失败:', error)
  }
}

const formatDate = (timestamp) => {
  return new Date(timestamp * 1000).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const handleSubscribe = async (plan) => {
  if (!userId.value) {
    router.push('/login')
    return
  }

  try {
    const token = localStorage.getItem('token')
    const response = await axios.post('/user/subscribe', {
      plan_id: plan.id
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })

    if (response.data.code === 200) {
      // 显示成功消息
      setTimeout(() => {
        router.push('/chat')
      }, 1500)
    }
  } catch (error) {
    console.error('订阅失败:', error)
  }
}

onMounted(() => {
  fetchSubscriptionInfo()
})
</script>

<style scoped>
.subscription-container {
  min-height: 100vh;
  background-color: #f8f9fa;
  padding: 2rem;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.subscription-content {
  max-width: 1200px;
  width: 100%;
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  padding: 2rem;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
}

.back-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background-color: #f8f9fa;
  border: 1px solid #e8eaed;
  border-radius: 4px;
  color: #5f6368;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-button:hover {
  background-color: #f1f3f4;
  border-color: #dadce0;
}

.back-button i {
  font-size: 0.875rem;
}

.subscription-title {
  margin-bottom: 0;
}

.status-card {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  border: 1px solid #e8eaed;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.status-header i {
  color: #1a73e8;
  font-size: 1.25rem;
}

.status-header h2 {
  font-size: 1.25rem;
  font-weight: 500;
  color: #202124;
  margin: 0;
}

.status-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.status-text {
  color: #5f6368;
  margin: 0;
  font-size: 1rem;
}

.plans-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
}

.plan-card {
  position: relative;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e8eaed;
  padding: 1.5rem;
  transition: all 0.3s ease;
}

.plan-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.plan-card:nth-child(2)::before {
  content: '最受欢迎';
  position: absolute;
  top: 0;
  right: 0;
  background-color: #1a73e8;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 0 8px 0 8px;
  font-size: 0.75rem;
  font-weight: 500;
}

.plan-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.plan-header h3 {
  font-size: 1.5rem;
  font-weight: 500;
  color: #202124;
  margin: 0 0 0.5rem 0;
}

.plan-price {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 0.25rem;
}

.price {
  font-size: 2rem;
  font-weight: 600;
  color: #1a73e8;
}

.period {
  color: #5f6368;
  font-size: 1rem;
}

.plan-features {
  margin: 1.5rem 0;
}

.plan-features ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.plan-features li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #5f6368;
  margin-bottom: 0.75rem;
  font-size: 1rem;
}

.plan-features li i {
  color: #1a73e8;
}

.subscribe-button {
  width: 100%;
  padding: 0.75rem 1.5rem;
  background-color: #1a73e8;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.subscribe-button:hover {
  background-color: #1557b0;
}

.subscribe-button.current-plan {
  background-color: #e8f0fe;
  color: #1a73e8;
  cursor: default;
}

.subscribe-button.current-plan:hover {
  background-color: #e8f0fe;
}

@media (max-width: 768px) {
  .subscription-container {
    padding: 1rem;
  }
  
  .subscription-content {
    padding: 1.5rem;
  }
  
  .plans-container {
    grid-template-columns: 1fr;
  }
}
</style> 