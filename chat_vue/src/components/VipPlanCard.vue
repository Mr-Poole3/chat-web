<template>
  <div class="vip-plan-modal" v-if="show" @click.self="closeModal">
    <div class="vip-plan-container" ref="modalContainer">
      <div class="header">
        <h2>会员升级</h2>
        <button @click="closeModal" class="close-button">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <div class="plans-container">
        <div v-if="loading" class="loading-wrapper">
          <div class="spinner"></div>
          <p>加载中...</p>
        </div>
        
        <div v-else class="plans-grid">
          <div v-for="plan in plans" :key="plan.id" class="plan-card" :class="{ 'recommended': plan.name === '月卡VIP' }">
            <div v-if="plan.name === '月卡VIP'" class="recommended-tag">推荐</div>
            <div class="plan-header">
              <h3>{{ plan.name }}</h3>
              <div class="price">
                <span class="amount">¥{{ plan.price }}</span>
                <span class="period" v-if="plan.name === '周卡VIP'">/周</span>
                <span class="period" v-else-if="plan.name === '月卡VIP'">/月</span>
                <span class="period" v-else-if="plan.name === '年卡VIP'">/年</span>
              </div>
              <div class="duration">{{ plan.duration_days }}天</div>
            </div>
            
            <div class="plan-features">
              <div class="feature-item">
                <span class="icon">✓</span>
                <span>解锁所有AI模型</span>
              </div>
              <div class="feature-item">
                <span class="icon">✓</span>
                <span>使用知识库功能</span>
              </div>
              <div class="feature-item">
                <span class="icon">✓</span>
                <span>访问所有高级工具</span>
              </div>
              <div class="feature-item">
                <span class="icon">✓</span>
                <span>优先客服支持</span>
              </div>
            </div>
            
            <div class="plan-action">
              <button @click="subscribe(plan)" class="subscribe-button">
                立即订阅
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <div class="footer">
        <p>升级VIP享受更多特权和功能，提升您的AI体验</p>
        <button @click="$router.push('/subscription')" class="view-more-button">
          查看更多订阅详情
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount, watch } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['close', 'subscribe']);
const router = useRouter();

const loading = ref(true);
const plans = ref([]);
const modalContainer = ref(null);

// 监听show属性变化
watch(() => props.show, async (newValue) => {
  if (newValue) {
    // 当modal显示时，加载数据
    await loadSubscriptionPlans();
    
    // 添加点击外部关闭事件和ESC键关闭事件
    nextTick(() => {
      document.addEventListener('keydown', handleEscKey);
    });
  } else {
    document.removeEventListener('keydown', handleEscKey);
  }
});

// ESC键关闭
const handleEscKey = (e) => {
  if (e.key === 'Escape') {
    closeModal();
  }
};

// 关闭Modal
const closeModal = () => {
  emit('close');
};

// 加载订阅计划
const loadSubscriptionPlans = async () => {
  try {
    loading.value = true;
    const token = localStorage.getItem('token');
    
    if (!token) {
      router.push('/login');
      return;
    }
    
    const response = await axios.get('/subscription/plans', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
    
    if (response.data.code === 200) {
      plans.value = response.data.data;
    }
  } catch (error) {
    console.error('获取订阅计划失败:', error);
  } finally {
    loading.value = false;
  }
};

// 订阅
const subscribe = async (plan) => {
  try {
    loading.value = true
    emit('subscribe', plan)
    // 延迟跳转，确保动画效果
    setTimeout(() => {
      router.push('/subscription')
    }, 300)
  } catch (error) {
    console.error('订阅处理失败:', error)
  } finally {
    loading.value = false
  }
}

// 组件销毁前移除事件监听器
onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleEscKey);
});
</script>

<style scoped>
.vip-plan-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
}

.vip-plan-container {
  background-color: #1e2130;
  border-radius: 12px;
  width: 90%;
  max-width: 900px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  animation: modalFadeIn 0.3s ease;
  border: 1px solid rgba(99, 102, 241, 0.2);
}

@keyframes modalFadeIn {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.2);
}

.header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #e0e0ff;
  background: linear-gradient(90deg, #4c4ed9, #6366f1);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.close-button {
  background: none;
  border: none;
  color: #a5b4fc;
  cursor: pointer;
  padding: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.close-button:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: #e0e0ff;
}

.plans-container {
  padding: 24px;
}

.loading-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.plan-card {
  background-color: rgba(30, 33, 48, 0.7);
  border-radius: 10px;
  border: 1px solid rgba(99, 102, 241, 0.3);
  padding: 20px;
  display: flex;
  flex-direction: column;
  position: relative;
  transition: transform 0.3s, box-shadow 0.3s;
}

.plan-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
}

.plan-card.recommended {
  border-color: #6366f1;
  box-shadow: 0 0 15px rgba(99, 102, 241, 0.3);
}

.recommended-tag {
  position: absolute;
  top: -10px;
  right: 20px;
  background: linear-gradient(90deg, #4c4ed9, #6366f1);
  color: white;
  padding: 5px 10px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: bold;
}

.plan-header {
  margin-bottom: 20px;
  text-align: center;
}

.plan-header h3 {
  margin: 0 0 10px 0;
  font-size: 1.25rem;
  color: #e0e0ff;
}

.price {
  margin-bottom: 5px;
}

.amount {
  font-size: 1.8rem;
  font-weight: bold;
  color: #6366f1;
}

.period {
  font-size: 0.9rem;
  color: #a5b4fc;
}

.duration {
  font-size: 0.9rem;
  color: #a5b4fc;
}

.plan-features {
  flex-grow: 1;
  margin-bottom: 20px;
}

.feature-item {
  display: flex;
  margin-bottom: 10px;
  align-items: center;
}

.icon {
  color: #6366f1;
  margin-right: 10px;
  font-weight: bold;
}

.plan-action {
  margin-top: auto;
}

.subscribe-button {
  width: 100%;
  padding: 10px;
  background: linear-gradient(90deg, #4c4ed9, #6366f1);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.subscribe-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(99, 102, 241, 0.3);
}

.footer {
  padding: 20px 24px;
  border-top: 1px solid rgba(99, 102, 241, 0.2);
  text-align: center;
}

.footer p {
  margin-bottom: 15px;
  color: #a5b4fc;
}

.view-more-button {
  background: none;
  border: 1px solid #6366f1;
  color: #6366f1;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.view-more-button:hover {
  background-color: rgba(99, 102, 241, 0.1);
}

@media (max-width: 768px) {
  .plans-grid {
    grid-template-columns: 1fr;
  }
  
  .vip-plan-container {
    width: 95%;
    max-height: 80vh;
  }
}
</style> 