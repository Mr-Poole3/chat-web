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
        :class="{ active: activeToolId === 'knowledge-base', 'disabled-tool': !isVip }"
        @click="handleToolClick('knowledge-base')"
      >
        <img src="https://img.icons8.com/?size=100&id=443&format=png&color=FFFFFF" alt="AI知识库">
        <span>AI知识库</span>
        <div v-if="!isVip" class="vip-tag">VIP</div>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'essay', 'disabled-tool': !isVip }" 
        @click="handleToolClick('essay')"
      >
        <img src="https://img.icons8.com/?size=100&id=42763&format=png&color=FFFFFF" alt="论文">
        <span>论文辅助阅读</span>
        <div v-if="!isVip" class="vip-tag">VIP</div>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'ppt', 'disabled-tool': !isVip }"
        @click="handleToolClick('ppt')"
      >
        <img src="https://img.icons8.com/?size=100&id=saSupsgVcmJe&format=png&color=FFFFFF" alt="PPT"/>
        <span>Open Manus</span>
        <div v-if="!isVip" class="vip-tag">VIP</div>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'resume', 'disabled-tool': !isVip }" 
        @click="handleToolClick('resume')"
      >
        <img src="https://img.icons8.com/?size=100&id=23877&format=png&color=FFFFFF" alt="简历">
        <span>简历生成器</span>
        <div v-if="!isVip" class="vip-tag">VIP</div>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'flowchart', 'disabled-tool': !isVip }" 
        @click="handleToolClick('flowchart')"
      >
        <img src="https://img.icons8.com/?size=100&id=1763&format=png&color=FFFFFF" alt="流程图">
        <span>流程图生成器</span>
        <div v-if="!isVip" class="vip-tag">VIP</div>
      </div>
      
      <!-- 订阅入口 -->
      <div 
        class="tool-item subscription-item" 
        @click="navigateTo('/subscription')"
      >
        <i class="fas fa-crown" style="color: gold; margin-right: 10px;"></i>
        <span>{{ isVip ? '会员中心' : '开通VIP会员' }}</span>
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
  },
  isVip: {
    type: Boolean,
    default: false
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

const handleToolClick = (toolId) => {
  if (!props.isVip) {
    navigateTo('/subscription')
    return
  }
  emit('load-tool', toolId)
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
  position: relative;
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

.vip-tag {
  position: absolute;
  right: 10px;
  background-color: #f59e0b;
  color: white;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: bold;
}

.subscription-item {
  margin-top: 20px;
  background-color: rgba(245, 158, 11, 0.2);
  border-radius: 8px;
}

.subscription-item:hover {
  background-color: rgba(245, 158, 11, 0.3);
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
  cursor: pointer;
}
/* --- END: Disabled Tool Styles --- */
</style> 