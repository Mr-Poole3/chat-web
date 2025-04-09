<template>
  <div class="chat-history">
    <div class="history-header">
      <h3>聊天历史</h3>
      <button class="new-chat-btn" @click="$emit('new-chat')">
        <i class="fas fa-plus"></i> 新对话
      </button>
    </div>
    
    <div class="history-list">
      <div
        v-for="chat in chatHistory"
        :key="chat.id"
        class="history-item"
        :class="{ active: chat.id === currentChatId }"
        @click="$emit('select-chat', chat.id)"
      >
        <div class="history-item-content">
          <div class="history-item-title">
            <i class="fas fa-comment"></i>
            {{ chat.title }}
          </div>
          <div class="history-item-info">
            <span class="model-tag">{{ chat.model }}</span>
            <span class="time">{{ formatTime(chat.updatedAt || chat.createdAt) }}</span>
          </div>
        </div>
        <div class="history-item-actions">
          <button 
            class="delete-btn"
            @click.stop="$emit('delete-chat', chat.id)"
            title="删除对话"
          >
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  chatHistory: {
    type: Array,
    required: true
  },
  currentChatId: {
    type: String,
    default: null
  }
})

defineEmits(['new-chat', 'select-chat', 'delete-chat'])

// 格式化时间
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  // 如果是今天
  if (diff < 24 * 60 * 60 * 1000) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  
  // 如果是昨天
  if (diff < 48 * 60 * 60 * 1000) {
    return '昨天'
  }
  
  // 如果是本周
  if (diff < 7 * 24 * 60 * 60 * 1000) {
    const days = ['日', '一', '二', '三', '四', '五', '六']
    return `星期${days[date.getDay()]}`
  }
  
  // 其他情况显示日期
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}
</script>

<style scoped>
.chat-history {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.history-header {
  padding: 16px;
  border-bottom: 1px solid #e5e5e5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-header h3 {
  margin: 0;
  font-size: 16px;
  color: #fff;
}

.new-chat-btn {
  padding: 6px 12px;
  background-color: #5658e4;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}

.new-chat-btn:hover {
  background-color: #121420;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.history-item {
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  transition: background-color 0.2s;
}

.history-item:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.history-item.active {
  background-color: rgba(0, 0, 0, 0.1);
}

.history-item-content {
  flex: 1;
  min-width: 0;
}

.history-item-title {
  font-size: 14px;
  color: #fff;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-item-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.model-tag {
  background-color: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.time {
  color: rgba(255, 255, 255, 0.5);
}

.history-item-actions {
  opacity: 0;
  transition: opacity 0.2s;
}

.history-item:hover .history-item-actions {
  opacity: 1;
}

.delete-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.delete-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: #ff4444;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .history-header {
    padding: 12px;
  }
  
  .history-item {
    padding: 10px;
  }
  
  .history-item-title {
    font-size: 13px;
  }
  
  .history-item-info {
    font-size: 11px;
  }
}
</style> 