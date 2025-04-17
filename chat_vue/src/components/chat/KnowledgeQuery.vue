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
        <button class="clear-kb-btn" @click="clearCurrentKb">
          <i class="fas fa-times"></i>
        </button>
      </div>
      
      <div class="input-container">
        <textarea 
          class="query-input" 
          v-model="queryText" 
          placeholder="请输入您的问题..."
          @keydown.enter.prevent="handleEnterKey"
          :disabled="isQuerying"
          rows="3"
        ></textarea>
        <button 
          class="query-button" 
          @click="sendQuery" 
          :disabled="!queryText.trim() || isQuerying">
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
      <div class="suggestion-questions">
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

// 清除当前知识库
const clearCurrentKb = () => {
  currentKbId.value = ''
  localStorage.removeItem('current_kb_id')
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
  if (!queryText.value.trim() || isQuerying.value) return
  
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
    const response = await fetch('/knowledge/query', {
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
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const text = decoder.decode(value)
      const events = text.split('\n\n').filter(e => e.trim() !== '')
      
      for (const event of events) {
        if (event.startsWith('data: ')) {
          const data = event.substring(6)
          
          if (data === '[DONE]') continue
          
          try {
            const jsonData = JSON.parse(data)
            
            // 处理Delta内容
            if (jsonData.choices && jsonData.choices[0].delta && jsonData.choices[0].delta.content) {
              const content = jsonData.choices[0].delta.content
              assistantResponse += content
              
              // 更新响应来源
              if (jsonData.source) {
                responseSource = jsonData.source
              }
              
              // 实时更新助手消息内容
              conversation.value[assistantMessageIndex] = {
                role: 'assistant',
                content: assistantResponse,
                source: responseSource
              }
            }
          } catch (error) {
            console.error('解析SSE数据时出错:', error)
          }
        }
      }
    }
    
    // 确保最终消息已更新
    conversation.value[assistantMessageIndex] = {
      role: 'assistant',
      content: assistantResponse || '抱歉，我无法回答这个问题。',
      source: responseSource
    }
    
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('请求被取消')
    } else {
      console.error('查询处理出错:', error)
      
      // 更新助手消息为错误状态
      conversation.value[assistantMessageIndex] = {
        role: 'assistant',
        content: `查询出错: ${error.message}`,
        error: true
      }
    }
  } finally {
    isQuerying.value = false
    queryText.value = '' // 清空输入
    queryController.value = null
  }
}

// 从localStorage获取当前知识库ID
onMounted(() => {
  const savedKbId = localStorage.getItem('current_kb_id')
  if (savedKbId) {
    currentKbId.value = savedKbId
  }
})
</script>

<style scoped>
.knowledge-query-container {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
  color: #e0e0ff;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #6366f1 #1e2130;
}

/* 滚动条样式 */
.knowledge-query-container::-webkit-scrollbar {
  width: 6px;
}

.knowledge-query-container::-webkit-scrollbar-track {
  background: #1e2130;
}

.knowledge-query-container::-webkit-scrollbar-thumb {
  background-color: #6366f1;
  border-radius: 3px;
}

.query-header {
  text-align: center;
  margin-bottom: 20px;
}

.query-header h2 {
  color: #e0e0ff;
  margin-bottom: 10px;
  font-size: 1.8rem;
  font-weight: 600;
}

.description {
  color: #a5b4fc;
  font-size: 1rem;
}

.query-input-section {
  margin-bottom: 20px;
}

.kb-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: rgba(99, 102, 241, 0.1);
  padding: 8px 12px;
  border-radius: 8px 8px 0 0;
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-bottom: none;
}

.kb-status-text {
  color: #a5b4fc;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

.clear-kb-btn {
  background: none;
  border: none;
  color: #a5b4fc;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.clear-kb-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: #e0e0ff;
}

.input-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  position: relative;
}

.query-input {
  width: 100%;
  padding: 15px;
  border-radius: 8px;
  background-color: rgba(30, 33, 48, 0.7);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #e0e0ff;
  font-size: 1rem;
  resize: vertical;
  min-height: 60px;
  outline: none;
  transition: all 0.3s ease;
}

.kb-status + .input-container .query-input {
  border-radius: 0 0 8px 8px;
}

.query-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.query-input:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.query-button {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background-color: #6366f1;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.query-button:hover:not(:disabled) {
  background-color: #4c4ed9;
  transform: translateY(-2px);
  box-shadow: 0 2px 5px rgba(76, 78, 229, 0.3);
}

.query-button:disabled {
  background-color: #444;
  cursor: not-allowed;
  opacity: 0.7;
}

.conversation-container {
  flex: 1;
  overflow-y: auto;
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  scrollbar-width: thin;
  scrollbar-color: #6366f1 #1e2130;
  padding-right: 5px;
}

.conversation-container::-webkit-scrollbar {
  width: 4px;
}

.conversation-container::-webkit-scrollbar-track {
  background: #1e2130;
}

.conversation-container::-webkit-scrollbar-thumb {
  background-color: #6366f1;
  border-radius: 2px;
}

.message {
  padding: 15px;
  border-radius: 12px;
  max-width: 100%;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user {
  background-color: rgba(99, 102, 241, 0.15);
  border-left: 3px solid #6366f1;
  align-self: flex-end;
}

.message.assistant {
  background-color: rgba(30, 33, 48, 0.7);
  border-left: 3px solid #10b981;
  align-self: flex-start;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.9rem;
}

.message-role {
  font-weight: bold;
  color: #a5b4fc;
  display: flex;
  align-items: center;
  gap: 6px;
}

.message.assistant .message-role {
  color: #10b981;
}

.message-source {
  font-size: 0.8rem;
  background-color: rgba(16, 185, 129, 0.1);
  color: #10b981;
  padding: 2px 6px;
  border-radius: 4px;
}

.message-content {
  color: #e0e0ff;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  word-break: break-word;
}

/* 支持Markdown样式 */
.message-content :deep(p) {
  margin: 0.5em 0;
}

.message-content :deep(code) {
  background-color: rgba(30, 33, 48, 0.5);
  padding: 2px 4px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9em;
}

.message-content :deep(pre) {
  background-color: rgba(30, 33, 48, 0.5);
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 1em 0;
}

.message-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
}

.message-content :deep(a) {
  color: #818cf8;
  text-decoration: none;
}

.message-content :deep(a:hover) {
  text-decoration: underline;
}

.message-content :deep(ul), .message-content :deep(ol) {
  padding-left: 1.5em;
  margin: 0.5em 0;
}

.message-content :deep(li) {
  margin: 0.3em 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #a5b4fc;
  opacity: 0.7;
  flex: 1;
  text-align: center;
}

.empty-icon {
  font-size: 60px;
  margin-bottom: 15px;
  color: #6366f1;
}

.suggestion-questions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
  max-width: 600px;
}

.suggestion-btn {
  background-color: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #a5b4fc;
  padding: 8px 12px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.9rem;
}

.suggestion-btn:hover {
  background-color: rgba(99, 102, 241, 0.2);
  border-color: rgba(99, 102, 241, 0.5);
  color: #e0e0ff;
  transform: translateY(-2px);
}

/* 移动端响应式适配 */
@media (max-width: 768px) {
  .knowledge-query-container {
    padding: 15px 10px;
  }
  
  .query-header h2 {
    font-size: 1.5rem;
  }
  
  .query-input {
    padding: 12px;
  }
  
  .message {
    padding: 12px;
  }
  
  .suggestion-questions {
    flex-direction: column;
    gap: 8px;
  }
  
  .suggestion-btn {
    width: 100%;
  }
}
</style> 