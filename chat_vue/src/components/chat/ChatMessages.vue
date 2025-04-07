<template>
  <div class="chat-container">
    <div class="welcome-screen" v-if="messages.length === 0">
      <h2 class="welcome-title">欢迎使用 天汇AI</h2>
      <!-- Lottie 动画 -->
      <DotLottieVue 
        class="welcome-animation" 
        autoplay 
        :loop="false" 
        src="https://lottie.host/075353b3-e4c2-4fa8-91ea-7f32563e1e3b/UQ3swQC3pC.lottie"
        @complete="$emit('animation-complete')"
      />
    </div>
    
    <div v-else>
      <div 
        v-for="(message, index) in messages" 
        :key="index" 
        :class="['message', message.role === 'user' ? 'user-message' : 'bot-message']"
      >
        <div :class="['avatar', message.role === 'user' ? 'user-avatar' : 'bot-avatar']">
          <template v-if="message.role === 'user'">🧑‍💻</template>
          <template v-else>🤖</template>
        </div>
        <div 
          class="message-content" 
          v-if="!message.streaming" 
          v-html="renderMarkdown(message.content)"
        ></div>
        <div class="message-content" v-else>
          <div v-if="message.content" v-html="renderMarkdown(message.content)"></div>
          <div class="typing-indicator">
            <div class="wave-dots">
              <div class="dot"></div>
              <div class="dot"></div>
              <div class="dot"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { DotLottieVue } from '@lottiefiles/dotlottie-vue'

defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  renderMarkdown: {
    type: Function,
    required: true
  }
})

defineEmits(['animation-complete'])
</script> 