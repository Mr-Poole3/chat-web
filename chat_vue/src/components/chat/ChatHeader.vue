<template>
  <div class="header">
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
        <i class="fas fa-sign-out-alt"></i> 退出
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

defineEmits(['change-model', 'logout'])
</script> 