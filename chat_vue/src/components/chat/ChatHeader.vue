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
  }
})

defineEmits(['change-model', 'logout', 'toggle-sidebar'])
</script>

<style scoped>
.header {
  position: relative;
}

.mobile-menu-button {
  display: none;
  color: #6366f1;
  font-size: 20px;
  cursor: pointer;
  margin-right: 15px;
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