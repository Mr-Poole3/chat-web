<template>
  <div class="header">
    <!-- 移动端菜单按钮 -->
    <div class="mobile-menu-button" @click="$emit('toggle-sidebar')">
      <i class="fas fa-bars"></i>
    </div>
    
    <select 
      :value="selectedModel" 
      @change="$emit('change-model', $event.target.value)" 
      :disabled="loading"
    >
      <option v-for="model in availableModels" :key="model.id" :value="model.id">
        {{ model.name }}
      </option>
    </select>
    <div class="user-menu">
      <router-link v-if="isVip" to="/subscription" class="subscription-link">
        <div class="vip-badge">
          <i class="fas fa-crown"></i> VIP
        </div>
      </router-link>
      <div v-else class="subscription-link" @click="$emit('open-vip-plan')">
        <div class="upgrade-badge">
          升级VIP
        </div>
      </div>
      <span id="username-display">
        <div class="user-avatar" id="user-avatar">{{ username ? username.charAt(0).toUpperCase() : 'U' }}</div>
        <span id="username-text">{{ username || '用户' }}</span>
      </span>
      <button id="logout-button" class="logout-button" @click="$emit('logout')">
        <i class="fas fa-sign-out-alt"></i> 
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  selectedModel: {
    type: String,
    required: true
  },
  availableModels: {
    type: Array,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  },
  username: {
    type: String,
    default: ''
  },
  isVip: {
    type: Boolean,
    default: false
  }
})

defineEmits(['change-model', 'logout', 'toggle-sidebar', 'open-vip-plan'])
</script>

<style scoped>
.header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.mobile-menu-button {
  display: none;
  color: #6366f1;
  font-size: 20px;
  cursor: pointer;
  margin-right: 15px;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 12px;
}

.subscription-link {
  text-decoration: none;
  margin-right: 8px;
}

.vip-badge {
  background-color: #f59e0b;
  color: white;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 4px;
}

.upgrade-badge {
  background-color: #3b82f6;
  color: white;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.2s ease;
}

.upgrade-badge:hover {
  background-color: #2563eb;
  transform: translateY(-2px);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #6366f1;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 8px;
}

@media (max-width: 768px) {
  .mobile-menu-button {
    display: flex;
  }
  
  .header {
    padding-left: 15px;
  }
  
  .user-menu {
    flex: 0;
  }
  
  #username-text {
    display: none;
  }
  
  .logout-button {
    padding: 6px;
  }
  
  .logout-button span {
    display: none;
  }
}
</style> 