<template>
  <div class="sidebar" :class="{ expanded }">
    <div class="sidebar-header">天汇AI</div>
    <div class="sidebar-tools">
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'chat' }" 
        @click="$emit('load-chat-tool')"
      >
        <img src="https://img.icons8.com/?size=100&id=37410&format=png&color=FFFFFF" alt="聊天">
        <span>AI Chat</span>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'knowledge-base' }"
        @click="$emit('load-tool', 'knowledge-base')"
      >
        <img src="https://img.icons8.com/?size=100&id=443&format=png&color=FFFFFF" alt="AI知识库">
        <span>AI知识库</span>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'essay' }" 
        @click="$emit('load-tool', 'essay')"
      >
        <img src="https://img.icons8.com/?size=100&id=42763&format=png&color=FFFFFF" alt="论文">
        <span>论文辅助阅读</span>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'ppt' }"
        @click="$emit('load-tool', 'ppt')"
      >
        <img src="https://img.icons8.com/?size=100&id=saSupsgVcmJe&format=png&color=FFFFFF" alt="PPT"/>
        <span>Open Manus</span>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'resume' }" 
        @click="$emit('load-tool', 'resume')"
      >
        <img src="https://img.icons8.com/?size=100&id=23877&format=png&color=FFFFFF" alt="简历">
        <span>简历生成器</span>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'flowchart' }" 
        @click="$emit('load-tool', 'flowchart')"
      >
        <img src="https://img.icons8.com/?size=100&id=1763&format=png&color=FFFFFF" alt="流程图">
        <span>流程图生成器</span>
      </div>
    </div>
    <div class="sidebar-content" v-if="activeToolId === 'chat'">
      <!-- 聊天历史记录 -->
      <ChatHistory
        :chatHistory="chatHistory"
        :currentChatId="currentChatId"
        @new-chat="handleNewChat"
        @select-chat="handleSelectChat"
        @delete-chat="handleDeleteChat"
      />
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { defineProps, defineEmits } from 'vue'
import ChatHistory from './ChatHistory.vue'

const router = useRouter()

const props = defineProps({
  expanded: {
    type: Boolean,
    default: false
  },
  activeToolId: {
    type: String,
    default: 'chat'
  },
  chatHistory: {
    type: Array,
    required: true
  },
  currentChatId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['load-chat-tool', 'load-tool', 'new-chat', 'select-chat', 'delete-chat'])

const handleNewChat = () => {
  emit('new-chat')
}

const handleSelectChat = (chatId) => {
  emit('select-chat', chatId)
}

const handleDeleteChat = (chatId) => {
  emit('delete-chat', chatId)
}

const navigateTo = (path) => {
  router.push(path)
}
</script>

<style scoped>
.sidebar {
  width: 260px;
  height: 100%;
  border-right: 1px solid rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  transition: transform 0.3s ease;
}

.sidebar-header {
  padding: 10px;
  font-size: 18px;
  font-weight: bold;
  color: #fff;
}

.sidebar-tools {
  display: flex;
  flex-direction: column;
  padding: 10px;
}

.tool-item {
  display: flex;
  align-items: center;
  padding: 10px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.tool-item:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.tool-item.active {
  background-color: rgba(0, 0, 0, 0.1);
}

.tool-item img {
  width: 24px;
  height: 24px;
  margin-right: 10px;
  filter: brightness(1);
}

.tool-item span {
  font-size: 16px;
  font-weight: bold;
  color: #ffffff;
}

.sidebar-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: -260px;
    top: 0;
    height: 100%;
    z-index: 1000;
    transition: left 0.3s ease;
  }
  
  .sidebar.expanded {
    left: 0;
    box-shadow: 2px 0 15px rgba(0, 0, 0, 0.3);
  }
}

/* --- START: Disabled Tool Styles --- */
.tool-item.disabled-tool img {
  filter: grayscale(100%);
  opacity: 0.6;
}

.tool-item.disabled-tool span {
  opacity: 0.7;
}

.tool-item.disabled-tool {
  cursor: not-allowed;
}
/* --- END: Disabled Tool Styles --- */
</style> 