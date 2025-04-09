<template>
  <div 
    class="vanishing-input-container"
    :class="{ 'submitting': isSubmitting }"
  >
    <button
      class="new-chat-button"
      @click="$emit('new-chat')"
      title="新对话"
    >
      <i class="fas fa-plus"></i>
    </button>
    <textarea
      ref="inputRef"
      :value="inputMessage"
      @input="handleInput"
      @keydown.enter.exact.prevent="handleSubmit"
      @keydown.enter.shift.exact="$emit('new-line', $event)"
      :disabled="loading"
      :placeholder="currentPlaceholder"
      class="vanishing-input"
      rows="1"
    ></textarea>
    <div class="button-group">
      <button
        v-if="loading"
        class="stop-button"
        @click="$emit('stop-generation')"
        title="停止生成"
      >
        <i class="fas fa-stop"></i>
      </button>
      <button
        class="send-button"
        @click="handleSubmit"
        :disabled="loading || !inputMessage.trim()"
      >
        <i class="fas fa-paper-plane"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  inputMessage: {
    type: String,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:inputMessage', 'send-message', 'new-line', 'stop-generation', 'new-chat'])
const inputRef = ref(null)

// 占位符数组
const placeholders = [
  "有什么我可以帮你的吗？",
  "问我任何问题...",
  "让我来协助你...",
  "输入你的问题..."
]

const currentPlaceholder = ref(placeholders[0])
const isSubmitting = ref(false)
let placeholderInterval

// 处理输入
const handleInput = (e) => {
  const textarea = e.target
  emit('update:inputMessage', textarea.value)
  
  // 自动调整高度
  textarea.style.height = 'auto'
  textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
}

// 处理提交
const handleSubmit = async () => {
  if (props.inputMessage.trim() && !props.loading) {
    isSubmitting.value = true
    // 等待动画完成
    await new Promise(resolve => setTimeout(resolve, 300))
    emit('send-message')
    // 重置提交状态和高度
    setTimeout(() => {
      isSubmitting.value = false
      if (inputRef.value) {
        inputRef.value.style.height = 'auto'
      }
    }, 100)
  }
}

// 循环显示占位符
const rotatePlaceholders = () => {
  let index = 0
  placeholderInterval = setInterval(() => {
    index = (index + 1) % placeholders.length
    currentPlaceholder.value = placeholders[index]
  }, 3000)
}

onMounted(() => {
  rotatePlaceholders()
})

onUnmounted(() => {
  if (placeholderInterval) {
    clearInterval(placeholderInterval)
  }
})
</script>

<style scoped>
.vanishing-input-container {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background-color: #161923;
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  padding: 12px 16px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  max-width: 1000px;
  width: 90%;
  margin: 16px auto;
}

.vanishing-input-container:focus-within {
  border-color: rgba(99, 102, 241, 0.5);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.1);
}

.new-chat-button {
  background-color: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  height: 36px;
  min-width: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  border-radius: 8px;
  margin-top: 2px;
}

.new-chat-button:hover {
  background-color: rgba(99, 102, 241, 0.1);
  color: rgba(255, 255, 255, 0.8);
}

.vanishing-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #fff;
  font-size: 16px;
  line-height: 1.5;
  outline: none;
  padding: 4px 0;
  transition: all 0.3s ease;
  resize: none;
  min-height: 24px;
  max-height: 200px;
  overflow-y: auto;
}

.vanishing-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.3s ease;
}

.vanishing-input:focus::placeholder {
  opacity: 0;
  transform: translateX(-10px);
}

/* 自定义滚动条样式 */
.vanishing-input::-webkit-scrollbar {
  width: 4px;
}

.vanishing-input::-webkit-scrollbar-track {
  background: transparent;
}

.vanishing-input::-webkit-scrollbar-thumb {
  background-color: rgba(99, 102, 241, 0.3);
  border-radius: 2px;
}

.vanishing-input::-webkit-scrollbar-thumb:hover {
  background-color: rgba(99, 102, 241, 0.5);
}

.button-group {
  display: flex;
  gap: 8px;
  z-index: 2;
  margin-top: 2px;
}

.send-button, .stop-button {
  background-color: #4f46e5;
  border: none;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  height: 36px;
  width: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.stop-button {
  background-color: #dc2626;
}

.send-button:hover {
  background-color: #4338ca;
  transform: translateY(-1px);
}

.stop-button:hover {
  background-color: #b91c1c;
  transform: translateY(-1px);
}

.send-button:disabled {
  background-color: #4f46e5;
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

button i {
  font-size: 14px;
}

/* 禁用状态样式 */
.vanishing-input:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* 动画效果 */
@keyframes slideLeft {
  0% {
    opacity: 1;
    transform: translateX(0);
  }
  100% {
    opacity: 0;
    transform: translateX(-100%);
  }
}

@keyframes slideRight {
  0% {
    opacity: 0;
    transform: translateX(100%);
  }
  100% {
    opacity: 1;
    transform: translateX(0);
  }
}

.vanishing-input-container.submitting .vanishing-input {
  animation: slideLeft 0.3s ease-out forwards;
  pointer-events: none;
}

.vanishing-input-container:not(.submitting) .vanishing-input {
  animation: slideRight 0.3s ease-out;
}

/* 提交时的波纹效果 */
@keyframes ripple {
  0% {
    transform: scale(0);
    opacity: 0.5;
  }
  100% {
    transform: scale(4);
    opacity: 0;
  }
}

.vanishing-input-container.submitting::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 20px;
  height: 20px;
  background: rgba(99, 102, 241, 0.2);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  animation: ripple 0.6s ease-out forwards;
}

/* 移动端适配 */
@media (max-width: 640px) {
  .vanishing-input-container {
    margin: 12px;
    padding: 8px 12px;
    width: calc(100% - 24px);
  }
  
  .vanishing-input {
    font-size: 14px;
  }
  
  .new-chat-button,
  .send-button,
  .stop-button {
    height: 32px;
    width: 32px;
  }
  
  button i {
    font-size: 12px;
  }
}
</style> 