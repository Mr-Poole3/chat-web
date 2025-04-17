<template>
  <div class="knowledge-base-tool">
    <div class="tool-header">
      <h2>智能文档处理</h2>
      <p class="description">上传文档，智能提取关键信息，支持多种文档格式</p>
    </div>

    <div class="upload-section">
      <div class="upload-area" 
           @dragover.prevent 
           @drop.prevent="handleDrop"
           @click="triggerFileInput"
           :class="{ 
             'dragging': isDragging, 
             'disabled': processing 
           }"
           @dragenter="!processing && (isDragging = true)"
           @dragleave="isDragging = false">
        <input type="file" 
               ref="fileInput" 
               @change="handleFileSelect" 
               accept=".pdf,.doc,.docx,.txt,.md"
               style="display: none">
        <div class="upload-content">
          <i class="fas" :class="processing ? 'fa-spinner fa-spin' : 'fa-cloud-upload-alt'"></i>
          <p v-if="!processing">{{ currentFile ? '更换文件' : '拖拽文件到此处或点击上传' }}</p>
          <p v-else>文件处理中，请等待...</p>
          <p class="supported-formats">支持格式: PDF, Word, TXT, Markdown</p>
        </div>
      </div>
    </div>

    <div class="task-status" v-if="taskStatus">
      <div class="status-indicator" :class="taskStatusClass">
        <i class="fas" :class="taskStatusIcon"></i>
        <span>{{ taskStatus }}</span>
      </div>
       
      <div class="query-link" v-if="currentKbId && !showQueryInput">
        <button class="query-btn" @click="showQueryInput = true">
          <i class="fas fa-question-circle"></i> 开始提问
        </button>
      </div>
    </div>

    <!-- 用户问题输入区域 -->
    <div class="query-section" v-if="showQueryInput && currentKbId">
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

    <!-- 对话结果区域 -->
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
        </div>
        <div class="message-content" v-html="formatMessage(message.content)"></div>
      </div>
    </div>

    <div class="processing-section" v-if="currentFile && !showQueryInput">
      <div class="file-info">
        <span class="file-name">{{ currentFile.name }}</span>
        <span class="file-size">({{ formatFileSize(currentFile.size) }})</span>
      </div>
      <div class="progress-container" v-if="processing || progress > 0">
        <div class="progress-bar">
          <div class="progress" :style="{ width: progress + '%' }"></div>
          <span class="progress-text">{{ progress }}%</span>
        </div>
        <div class="progress-status">{{ progressStatus }}</div>
      </div>
      <div class="action-buttons">
        <button @click="processFile" 
                :disabled="processing || !currentFile" 
                class="process-btn">
          <i class="fas fa-play-circle" v-if="!processing"></i>
          <i class="fas fa-spinner fa-spin" v-else></i>
          {{ processing ? '处理中...' : '开始处理' }}
        </button>
        <button @click="cancelProcess" v-if="processing" class="cancel-btn">
          <i class="fas fa-stop-circle"></i>
          取消
        </button>
      </div>
    </div>

    <div class="empty-state" v-if="!currentFile && !processing && !showQueryInput">
      <i class="fas fa-file-alt empty-icon"></i>
      <p>上传文档开始提取知识</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import { marked } from 'marked'

const fileInput = ref(null)
const isDragging = ref(false)
const currentFile = ref(null)
const processing = ref(false)
const progress = ref(0)
const results = ref([])
const taskStatus = ref('')
const processingStage = ref('')
const cancelTokenSource = ref(null)
const currentKbId = ref('')

// 新增：查询相关变量
const showQueryInput = ref(false)
const queryText = ref('')
const isQuerying = ref(false)
const conversation = ref([])
const queryController = ref(null)

// 任务状态样式
const taskStatusClass = computed(() => {
  if (taskStatus.value.includes('成功')) return 'status-success'
  if (taskStatus.value.includes('失败') || taskStatus.value.includes('错误')) return 'status-error'
  if (taskStatus.value.includes('处理中')) return 'status-processing'
  return 'status-info'
})

// 任务状态图标
const taskStatusIcon = computed(() => {
  if (taskStatus.value.includes('成功')) return 'fa-check-circle'
  if (taskStatus.value.includes('失败') || taskStatus.value.includes('错误')) return 'fa-exclamation-circle'
  if (taskStatus.value.includes('处理中')) return 'fa-spinner fa-spin'
  return 'fa-info-circle'
})

// 进度状态文本
const progressStatus = computed(() => {
  if (processing.value) {
    if (progress.value < 25) return '正在上传文件...'
    if (progress.value < 50) return '正在分析文档结构...'
    if (progress.value < 75) return '提取关键信息...'
    return '生成知识结果...'
  }
  return progress.value === 100 ? '处理完成' : ''
})

const triggerFileInput = () => {
  if (!processing.value) {
    fileInput.value.click()
  }
}

const handleDrop = (e) => {
  if (processing.value) return
  
  isDragging.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) {
    handleFile(files[0])
  }
}

const handleFileSelect = (e) => {
  const files = e.target.files
  if (files.length > 0) {
    handleFile(files[0])
  }
}

const handleFile = (file) => {
  if (!isValidFileType(file)) {
    showToast('不支持的文件格式', 'error')
    return
  }
  currentFile.value = file
  progress.value = 0
  taskStatus.value = '文件已选择，待处理'
}

const isValidFileType = (file) => {
  const validTypes = ['.pdf', '.doc', '.docx', '.txt', '.md']
  const extension = '.' + file.name.split('.').pop().toLowerCase()
  return validTypes.includes(extension)
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const showToast = (message, type = 'info') => {
  // 简单的提示实现，可以替换为更复杂的通知组件
  alert(message)
}

const processFile = async () => {
  if (!currentFile.value || processing.value) return

  processing.value = true
  progress.value = 0
  processingStage.value = 'uploading'
  taskStatus.value = '文档处理中...'

  const formData = new FormData()
  formData.append('file', currentFile.value)

  // 创建取消令牌
  cancelTokenSource.value = axios.CancelToken.source()

  try {
    // 获取token
    const token = localStorage.getItem('token')
    
    const response = await axios.post('/knowledge/process', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      cancelToken: cancelTokenSource.value.token,
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 40) / progressEvent.total)
        progress.value = percentCompleted
        
        if (percentCompleted >= 40) {
          processingStage.value = 'analyzing'
          // 模拟处理进度
          simulateProcessing()
        }
      }
    })

    if (response.data && response.data.kb_id) {
      currentKbId.value = response.data.kb_id
      localStorage.setItem('current_kb_id', response.data.kb_id)
      taskStatus.value = '处理成功，可以开始提问'
      // 隐藏结果，只提供提问按钮
      results.value = []
    } else {
      taskStatus.value = '处理完成，但未生成知识库ID'
    }
  } catch (error) {
    console.error('处理文件时出错:', error)
    
    if (axios.isCancel(error)) {
      taskStatus.value = '处理已取消'
      showToast('文档处理已取消')
    } else {
      taskStatus.value = '处理失败'
      showToast('处理文件时出错，请重试', 'error')
    }
  } finally {
    processing.value = false
    cancelTokenSource.value = null
  }
}

const simulateProcessing = () => {
  // 模拟文档处理进度
  const interval = setInterval(() => {
    if (processing.value) {
      if (progress.value < 95) {
        progress.value += 3
        
        if (progress.value >= 60 && processingStage.value === 'analyzing') {
          processingStage.value = 'extracting'
        }
        
        if (progress.value >= 80 && processingStage.value === 'extracting') {
          processingStage.value = 'finalizing'
        }
      }
    } else {
      clearInterval(interval)
    }
  }, 300)
}

const cancelProcess = () => {
  if (cancelTokenSource.value) {
    cancelTokenSource.value.cancel()
    progress.value = 0
    processing.value = false
    taskStatus.value = '处理已取消'
  }
}

// 处理Enter键按下
const handleEnterKey = (e) => {
  if (!e.shiftKey) {
    sendQuery()
  }
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
      stream: true,
      kb_id: currentKbId.value
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
    
    // 更新助手消息内容
    conversation.value[assistantMessageIndex] = {
      role: 'assistant',
      content: ''
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
              
              // 实时更新助手消息内容
              conversation.value[assistantMessageIndex] = {
                role: 'assistant',
                content: assistantResponse
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
      content: assistantResponse || '抱歉，我无法回答这个问题。'
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
</script>

<style scoped>
.knowledge-base-tool {
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
.knowledge-base-tool::-webkit-scrollbar {
  width: 6px;
}

.knowledge-base-tool::-webkit-scrollbar-track {
  background: #1e2130;
}

.knowledge-base-tool::-webkit-scrollbar-thumb {
  background-color: #6366f1;
  border-radius: 3px;
}

.tool-header {
  text-align: center;
  margin-bottom: 30px;
}

.tool-header h2 {
  color: #e0e0ff;
  margin-bottom: 10px;
  font-size: 1.8rem;
  font-weight: 600;
}

.description {
  color: #a5b4fc;
  font-size: 1rem;
}

.upload-section {
  margin-bottom: 30px;
}

.upload-area {
  border: 2px dashed #4c4ed9;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: rgba(30, 33, 48, 0.7);
}

.upload-area:hover:not(.disabled), .upload-area.dragging {
  border-color: #6366f1;
  background-color: rgba(99, 102, 241, 0.1);
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
}

.upload-area.disabled {
  opacity: 0.7;
  cursor: wait;
}

.upload-content {
  color: #a5b4fc;
}

.upload-content i {
  font-size: 48px;
  color: #6366f1;
  margin-bottom: 15px;
}

.supported-formats {
  font-size: 0.8em;
  color: #8b8ecc;
  margin-top: 10px;
}

.task-status {
  padding: 10px 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  text-align: center;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.9rem;
}

.status-indicator i {
  margin-right: 8px;
}

.status-success {
  background-color: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.status-error {
  background-color: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.status-processing {
  background-color: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
}

.status-info {
  background-color: rgba(99, 102, 241, 0.2);
  color: #6366f1;
}

.processing-section {
  margin: 20px 0;
  padding: 20px;
  background-color: rgba(30, 33, 48, 0.7);
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.2);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.file-info {
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.file-name {
  font-weight: bold;
  color: #e0e0ff;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  color: #a5b4fc;
}

.progress-container {
  margin: 15px 0;
}

.progress-bar {
  height: 20px;
  background-color: rgba(22, 25, 35, 0.8);
  border-radius: 10px;
  overflow: hidden;
  position: relative;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.2);
}

.progress {
  height: 100%;
  background: linear-gradient(90deg, #4c4ed9 0%, #6366f1 50%, #818cf8 100%);
  transition: width 0.5s ease;
  position: relative;
  overflow: hidden;
}

.progress::after {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  right: 0;
  background-image: linear-gradient(
    -45deg,
    rgba(255, 255, 255, 0.1) 25%,
    transparent 25%,
    transparent 50%,
    rgba(255, 255, 255, 0.1) 50%,
    rgba(255, 255, 255, 0.1) 75%,
    transparent 75%,
    transparent
  );
  background-size: 50px 50px;
  animation: progressStripes 2s linear infinite;
}

@keyframes progressStripes {
  0% {
    background-position: 0 0;
  }
  100% {
    background-position: 50px 0;
  }
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #fff;
  font-size: 0.8em;
  font-weight: bold;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.progress-status {
  color: #a5b4fc;
  font-size: 0.9em;
  text-align: center;
  margin-top: 8px;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 15px;
}

.process-btn, .cancel-btn, .clear-btn, .action-btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 100px;
}

.process-btn {
  background-color: #6366f1;
  color: white;
}

.process-btn:hover:not(:disabled) {
  background-color: #4c4ed9;
  transform: translateY(-2px);
  box-shadow: 0 2px 5px rgba(76, 78, 229, 0.3);
}

.process-btn:disabled {
  background-color: #444;
  cursor: not-allowed;
  opacity: 0.7;
}

.cancel-btn {
  background-color: #dc3545;
  color: white;
}

.cancel-btn:hover {
  background-color: #c82333;
  transform: translateY(-2px);
  box-shadow: 0 2px 5px rgba(220, 53, 69, 0.3);
}

.query-link {
  display: flex;
  justify-content: center;
  margin-top: 15px;
}

.query-btn {
  background-color: #10b981;
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

.query-btn:hover {
  background-color: #059669;
  transform: translateY(-2px);
  box-shadow: 0 2px 5px rgba(16, 185, 129, 0.3);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #a5b4fc;
  opacity: 0.7;
}

.empty-icon {
  font-size: 60px;
  margin-bottom: 15px;
  color: #6366f1;
}

/* 查询输入样式 */
.query-section {
  margin: 20px 0;
  padding: 20px;
  background-color: rgba(30, 33, 48, 0.7);
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.2);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.input-container {
  display: flex;
  flex-direction: column;
  position: relative;
}

.query-input {
  width: 100%;
  padding: 15px;
  padding-right: 60px;
  border-radius: 8px;
  background-color: rgba(22, 25, 35, 0.8);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #e0e0ff;
  font-size: 1rem;
  resize: vertical;
  min-height: 60px;
  outline: none;
  transition: all 0.3s ease;
}

.query-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
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

/* 对话样式 */
.conversation-container {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 500px;
  overflow-y: auto;
  padding-right: 5px;
  scrollbar-width: thin;
  scrollbar-color: #6366f1 #1e2130;
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

/* 移动端响应式适配 */
@media (max-width: 768px) {
  .knowledge-base-tool {
    padding: 15px 10px;
  }
  
  .tool-header h2 {
    font-size: 1.5rem;
  }
  
  .upload-area {
    padding: 25px 15px;
  }
  
  .upload-content i {
    font-size: 36px;
  }
  
  .processing-section,
  .query-section {
    padding: 15px;
  }
  
  .query-input {
    padding: 12px;
    font-size: 0.9rem;
  }
  
  .file-name {
    font-size: 0.9rem;
    max-width: 200px;
  }
  
  .action-buttons {
    justify-content: center;
  }
  
  .process-btn, .cancel-btn, .query-btn {
    min-width: 120px;
    padding: 8px 12px;
    font-size: 0.9rem;
  }
  
  .message {
    padding: 12px;
  }
}
</style> 