<template>
  <div class="knowledge-query-container">
    <div class="query-header">
      <h2>知识库问答</h2>
      <p class="description">提问关于文档内容的问题，获取智能回答</p>
    </div>

    <div class="query-input-section">
      <div class="kb-status" v-if="currentKbId">
        <span class="kb-status-text">
          <i class="fas fa-database"></i> 当前知识库: {{ formatKbId(currentKbId) }}
        </span>
        <div class="kb-actions">
          <button class="change-kb-btn" @click="goToKnowledgeList">
            <i class="fas fa-exchange-alt"></i> 更换
          </button>
          <button class="clear-kb-btn" @click="clearCurrentKb">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
      
      <div v-else class="no-kb-selected">
        <p>未选择知识库</p>
        <button class="select-kb-btn" @click="goToKnowledgeList">
          <i class="fas fa-database"></i> 选择知识库
        </button>
      </div>
      
      <div class="input-container">
        <textarea 
          class="query-input" 
          v-model="queryText" 
          placeholder="请输入您的问题..."
          @keydown.enter.prevent="handleEnterKey"
          :disabled="isQuerying || !currentKbId"
          rows="3"
        ></textarea>
        <button 
          class="query-button" 
          @click="sendQuery" 
          :disabled="!queryText.trim() || isQuerying || !currentKbId">
          <i class="fas" :class="isQuerying ? 'fa-spinner fa-spin' : 'fa-paper-plane'"></i>
          {{ isQuerying ? '查询中...' : '提问' }}
        </button>
      </div>
    </div>

    <div class="conversation-container" v-if="conversation.length > 0">
      <div 
        v-for="(message, index) in conversation" 
        :key="index" 
        class="message"
        :class="[message.role]"
      >
        <div class="message-header">
          <span class="message-role">
            <i class="fas" :class="message.role === 'user' ? 'fa-user' : 'fa-robot'"></i>
            {{ message.role === 'user' ? '您' : '知识助手' }}
          </span>
          <span class="message-source" v-if="message.source">
            {{ message.source === 'knowledge_base' ? '来自知识库' : '来自AI' }}
          </span>
        </div>
        <div class="message-content" v-html="formatMessage(message.content)"></div>
      </div>
    </div>

    <div class="empty-state" v-if="conversation.length === 0">
      <i class="fas fa-question-circle empty-icon"></i>
      <p>提问关于已上传文档的问题</p>
      <div class="suggestion-questions" v-if="currentKbId">
        <button 
          v-for="(question, index) in exampleQuestions" 
          :key="index"
          class="suggestion-btn"
          @click="useExampleQuestion(question)"
        >
          {{ question }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { marked } from 'marked'

const queryText = ref('')
const isQuerying = ref(false)
const conversation = ref([])
const currentKbId = ref('')
const queryController = ref(null)

// 示例问题
const exampleQuestions = [
  '文档的主要内容是什么？',
  '能总结一下关键信息吗？',
  '文档中有哪些重要概念？',
  '这个文档的结论是什么？'
]

// 格式化知识库ID显示
const formatKbId = (id) => {
  return id.slice(0, 8) + '...'
}

// 导航到知识库列表
const goToKnowledgeList = () => {
  // 使用非标准的方式切换到知识库列表标签
  const parentComponent = document.querySelector('.knowledge-manager')
  if (parentComponent) {
    const tabButtons = parentComponent.querySelectorAll('.tab')
    // 点击知识库列表标签
    if (tabButtons && tabButtons.length > 1) {
      tabButtons[1].click() // 第二个标签是知识库列表
    }
  }
}

// 清除当前知识库
const clearCurrentKb = () => {
  currentKbId.value = ''
  localStorage.removeItem('current_kb_id')
  
  // 清空对话历史
  conversation.value = []
}

// 处理Enter键按下
const handleEnterKey = (e) => {
  if (!e.shiftKey) {
    sendQuery()
  }
}

// 使用示例问题
const useExampleQuestion = (question) => {
  queryText.value = question
}

// 格式化消息内容(支持Markdown)
const formatMessage = (content) => {
  try {
    return marked(content)
  } catch (error) {
    return content
  }
}

// 发送查询
const sendQuery = async () => {
  if (!queryText.value.trim() || isQuerying.value || !currentKbId.value) return
  
  const query = queryText.value.trim()
  
  // 添加用户消息到对话中
  conversation.value.push({
    role: 'user',
    content: query
  })
  
  // 添加临时助手消息（等待响应）
  const assistantMessageIndex = conversation.value.length
  conversation.value.push({
    role: 'assistant',
    content: '思考中...',
    isLoading: true
  })
  
  isQuerying.value = true
  
  // 如果有正在进行的请求，取消它
  if (queryController.value) {
    queryController.value.abort()
  }
  
  // 创建新的AbortController
  queryController.value = new AbortController()
  
  try {
    // 获取token
    const token = localStorage.getItem('token')
    
    // 准备请求数据
    const requestData = {
      query: query,
      stream: true
    }
    
    // 如果有当前知识库ID，则添加到请求中
    if (currentKbId.value) {
      requestData.kb_id = currentKbId.value
    }
    
    // 发送请求
    const response = await fetch('/api/v1/knowledge/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify(requestData),
      signal: queryController.value.signal
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    // 处理流式响应
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let assistantResponse = ''
    let responseSource = 'ai' // 默认来源
    
    // 更新助手消息内容
    conversation.value[assistantMessageIndex] = {
      role: 'assistant',
      content: '',
      source: responseSource
    }
    
    // 清空输入框
    queryText.value = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const text = decoder.decode(value)
      assistantResponse += text
      
      // 更新显示的回答
      conversation.value[assistantMessageIndex].content = assistantResponse
      
      // 检测回答来源
      if (assistantResponse.includes('来自知识库') || assistantResponse.includes('根据文档')) {
        conversation.value[assistantMessageIndex].source = 'knowledge_base'
      }
    }
  } catch (error) {
    console.error('发送查询请求失败:', error)
    
    // 更新助手消息为错误信息
    if (assistantMessageIndex < conversation.value.length) {
      conversation.value[assistantMessageIndex].content = '抱歉，查询过程中发生错误，请重试。'
      conversation.value[assistantMessageIndex].isError = true
    }
  } finally {
    isQuerying.value = false
    queryController.value = null
  }
}

onMounted(() => {
  // 从localStorage获取当前知识库ID
  const storedKbId = localStorage.getItem('current_kb_id')
  if (storedKbId) {
    currentKbId.value = storedKbId
  }
})
</script>

<style scoped>
.knowledge-query-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.query-header h2 {
  margin: 0 0 5px 0;
  font-size: 1.8rem;
  color: #e0e0ff;
}

.query-header .description {
  margin: 0 0 20px 0;
  color: #9f9fb8;
  font-size: 0.9rem;
}

.query-input-section {
  margin-bottom: 20px;
}

.kb-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(30, 34, 45, 0.7);
  padding: 10px 15px;
  border-radius: 8px;
  margin-bottom: 15px;
  border-left: 3px solid #6366f1;
}

.kb-status-text {
  display: flex;
  align-items: center;
}

.kb-status-text i {
  color: #6366f1;
  margin-right: 8px;
}

.kb-actions {
  display: flex;
  gap: 10px;
}

.change-kb-btn {
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
  border: none;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 0.75rem;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.change-kb-btn i {
  margin-right: 4px;
}

.clear-kb-btn {
  background: rgba(220, 38, 38, 0.1);
  color: #ef4444;
  border: none;
  border-radius: 4px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.no-kb-selected {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(220, 38, 38, 0.1);
  padding: 10px 15px;
  border-radius: 8px;
  margin-bottom: 15px;
  border-left: 3px solid #ef4444;
}

.select-kb-btn {
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 5px 10px;
  font-size: 0.85rem;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.select-kb-btn i {
  margin-right: 5px;
}

.input-container {
  position: relative;
}

.query-input {
  width: 100%;
  padding: 15px;
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 8px;
  background: rgba(30, 34, 45, 0.7);
  color: #e0e0ff;
  font-family: inherit;
  font-size: 1rem;
  resize: none;
}

.query-input:focus {
  outline: none;
  border-color: #6366f1;
}

.query-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.query-button {
  position: absolute;
  bottom: 15px;
  right: 15px;
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}

.query-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.conversation-container {
  flex: 1;
  overflow-y: auto;
  padding: 10px 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message {
  padding: 15px;
  border-radius: 8px;
  max-width: 95%;
}

.user {
  align-self: flex-end;
  background: rgba(99, 102, 241, 0.1);
  border-right: 3px solid #6366f1;
}

.assistant {
  align-self: flex-start;
  background: rgba(30, 34, 45, 0.7);
  border-left: 3px solid #10b981;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.message-role {
  font-weight: 600;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
}

.message-role i {
  margin-right: 5px;
  color: #6366f1;
}

.assistant .message-role i {
  color: #10b981;
}

.message-source {
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
}

.message-content {
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: break-word;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.empty-icon {
  font-size: 3rem;
  color: #6366f1;
  margin-bottom: 20px;
}

.suggestion-questions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 20px;
  max-width: 600px;
}

.suggestion-btn {
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 20px;
  padding: 8px 15px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.suggestion-btn:hover {
  background: rgba(99, 102, 241, 0.2);
}
</style> 