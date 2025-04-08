<template>
  <div class="input-container">
    <div class="input-box">
      <button id="new-chat-button" class="input-button new-chat-button" @click="$emit('new-chat')" title="新建会话">
        <svg viewBox="0 0 1024 1024" width="24" height="24">
          <path d="M904.2 344.3c-21.5-50.7-52.2-96.3-91.3-135.4s-84.6-69.8-135.4-91.3C625 95.5 569.3 84.2 511.8 84.2S398.5 95.5 346 117.7c-50.7 21.5-96.3 52.2-135.4 91.3s-69.8 84.6-91.3 135.4c-22.2 52.5-33.5 108.3-33.5 165.8S97.1 623.5 119.3 676c21.5 50.7 52.2 96.3 91.3 135.4 39.1 39.1 84.6 69.8 135.4 91.3 52.5 22.2 108.3 33.5 165.8 33.5s113.3-11.3 165.8-33.5c50.7-21.5 96.3-52.2 135.4-91.3 39.1-39.1 69.8-84.6 91.3-135.4 22.2-52.5 33.5-108.3 33.5-165.8s-11.4-113.4-33.6-165.9zM511.8 876C310 876 145.9 711.8 145.9 510.1S310 144.2 511.8 144.2c201.7 0 365.9 164.1 365.9 365.9 0 201.7-164.2 365.9-365.9 365.9z" fill="#e6e6e6"></path>
          <path d="M737 481H542V286c0-16.5-13.5-30-30-30s-30 13.5-30 30v195H287c-16.5 0-30 13.5-30 30s13.5 30 30 30h195v195c0 16.5 13.5 30 30 30s30-13.5 30-30V541h195c16.5 0 30-13.5 30-30s-13.5-30-30-30z" fill="#e6e6e6"></path>
        </svg>
      </button>
      <textarea
        :value="inputMessage"
        @input="$emit('update:inputMessage', $event.target.value)"
        placeholder="发送消息..."
        @keydown.enter.exact.prevent="$emit('send-message')"
        @keydown.enter.shift.exact="$emit('new-line', $event)"
        :disabled="loading"
        id="user-input"
        rows="1"
      ></textarea>
      <button 
        id="send-button" 
        class="input-button send-button"
        @click="$emit('send-message')" 
        :disabled="loading || !inputMessage.trim()"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  inputMessage: {
    type: String,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:inputMessage', 'send-message', 'new-line', 'new-chat'])
</script>

<style scoped>
/* 移动端样式适配 */
@media (max-width: 576px) {
  .input-button {
    position: relative !important;
    bottom: auto !important;
    transform: translateY(0) !important;
  }
  
  .new-chat-button {
    margin-right: 8px;
  }
  
  .send-button {
    margin-left: 8px;
  }
  
  #user-input {
    padding: 10px 12px !important;
  }
  
  .input-box {
    align-items: center !important;
  }
}
</style> 