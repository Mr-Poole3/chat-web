<template>
  <div class="knowledge-base-tool">
    <div class="tool-header">
      <h2>智能文档处理</h2>
      <p class="description">上传文档，智能提取关键信息，支持多种文档格式</p>
    </div>

    <!-- 上传区域，当处理中或已完成时隐藏 -->
    <div class="upload-section" v-if="!processing && !currentKbId">
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

    <!-- 新增：知识库列表组件，修改条件确保正确显示 -->
    <div class="kb-list-section" v-if="!processing && (!currentKbId || (currentKbId && !showQueryInput))">
      <div class="section-header">
        <h3><i class="fas fa-database"></i> 我的知识库</h3>
        <button class="refresh-btn" @click="fetchKnowledgeBaseList" :disabled="isLoadingKBs">
          <i class="fas" :class="isLoadingKBs ? 'fa-spinner fa-spin' : 'fa-sync-alt'"></i>
        </button>
      </div>
      
      <div class="kb-list" v-if="knowledgeBaseList.length > 0">
        <div v-for="kb in knowledgeBaseList" :key="kb.kb_id" 
             class="kb-item"
             :class="{'kb-selected': kb.kb_id === currentKbId}">
          <div class="kb-details" @click="selectKnowledgeBase(kb.kb_id)">
            <div class="kb-icon">
              <i class="fas fa-book"></i>
            </div>
            <div class="kb-info">
              <div class="kb-name">{{ kb.file_name || '未命名知识库' }}</div>
              <div class="kb-date">{{ formatDate(kb.create_time) }}</div>
            </div>
          </div>
          <div class="kb-actions">
            <button class="kb-action-btn query" v-if="kb.kb_id === currentKbId" @click.stop="showQueryInput = true">
              <i class="fas fa-comment-dots"></i>
            </button>
            <button class="kb-action-btn delete" @click.stop="confirmDeleteKB(kb.kb_id)">
              <i class="fas fa-trash-alt"></i>
            </button>
          </div>
        </div>
      </div>
      
      <div class="kb-empty-state" v-else-if="!isLoadingKBs">
        <i class="fas fa-database"></i>
        <p>暂无知识库，请上传文档创建</p>
      </div>
      
      <div class="kb-loading" v-else>
        <i class="fas fa-spinner fa-spin"></i>
        <p>加载知识库中...</p>
      </div>
    </div>

    <!-- 新增：知识库选择后的提问界面 -->
    <div class="selected-kb-info" v-if="currentKbId && selectedKB && !showQueryInput">
      <div class="kb-header">
        <div class="kb-title">
          <i class="fas fa-book"></i>
          <h3>{{ selectedKB.file_name || '未命名知识库' }}</h3>
        </div>
        <div class="kb-actions">
          <button class="kb-back-btn" @click="resetKnowledgeBase">
            <i class="fas fa-arrow-left"></i> 返回列表
          </button>
        </div>
      </div>
      <p class="kb-description">您可以向此知识库提问任何问题，AI 将基于文档内容回答。</p>
    </div>

    <!-- Lottie动画加载区域，只在处理中显示 -->
    <div class="loading-animation-container" v-if="processing">
      <DotLottieVue 
        style="height: 300px; width: 300px" 
        autoplay 
        loop 
        src="https://lottie.host/1ad4e652-5209-4043-bb4b-b45f34842a8e/yLww9M6qdp.lottie" 
      />
      <p class="loading-text">{{ processingStage === 'uploading' ? '正在上传文件...' : '正在分析文档...' }}</p>
    </div>

    <div class="task-status" v-if="taskStatus && !processing">
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

    <!-- 修改提问界面条件，确保可以正确显示 -->
    <div class="query-section" v-if="showQueryInput && currentKbId">
      <div class="header-with-back">
        <button class="back-btn" @click="showQueryInput = false">
          <i class="fas fa-arrow-left"></i> 返回
        </button>
        <h3 v-if="selectedKB">{{ selectedKB.file_name || '未命名知识库' }}</h3>
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

    <!-- 对话结果区域 -->
    <div class="conversation-container" v-if="conversation.length > 0">
      <div 
        v-for="(message, index) in conversation" 
        :key="index" 
        class="message"
        :class="[message.role]"
      >
        <div class="message-content" v-html="formatMessage(message.content)"></div>
      </div>
    </div>

    <div class="action-section" v-if="currentFile && !showQueryInput && !processing">
      <div class="file-info">
        <span class="file-name">{{ currentFile.name }}</span>
        <span class="file-size">({{ formatFileSize(currentFile.size) }})</span>
      </div>
      <div class="action-buttons">
        <button @click="processFile" 
                :disabled="processing || !currentFile" 
                class="process-btn">
          <i class="fas fa-play-circle" v-if="!processing"></i>
          <i class="fas fa-spinner fa-spin" v-else></i>
          {{ processing ? '处理中...' : '开始处理' }}
        </button>
      </div>
    </div>

    <div class="empty-state" v-if="!currentFile && !processing && !showQueryInput && !currentKbId">
      <i class="fas fa-file-alt empty-icon"></i>
      <p>上传文档开始提取知识</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { marked } from 'marked'
import { DotLottieVue } from '@lottiefiles/dotlottie-vue'

const fileInput = ref(null)
const isDragging = ref(false)
const currentFile = ref(null)
const processing = ref(false)
const results = ref([])
const taskStatus = ref('')
const processingStage = ref('')
const cancelTokenSource = ref(null)
const currentKbId = ref('')

// 新增：知识库列表相关变量
const knowledgeBaseList = ref([])
const isLoadingKBs = ref(false)
const selectedKB = ref(null)

// 查询相关变量
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

// 组件加载时获取知识库列表
onMounted(() => {
  fetchKnowledgeBaseList()
  
  // 检查是否有缓存的知识库ID
  const cachedKbId = localStorage.getItem('current_kb_id')
  const userId = getUserId()
  if (cachedKbId) {
    // 添加用户ID校验，确保知识库属于当前用户
    currentKbId.value = cachedKbId
    fetchKnowledgeBaseDetails(cachedKbId)
  }
})

// 获取当前用户ID
const getUserId = () => {
  // 从localStorage获取用户信息
  const userInfo = localStorage.getItem('userInfo')
  if (userInfo) {
    try {
      const user = JSON.parse(userInfo)
      return user.id || user.userId || null
    } catch (e) {
      console.error('解析用户信息失败:', e)
    }
  }
  
  // 从token中解析用户ID（如果无法直接获取）
  const token = localStorage.getItem('token')
  if (token) {
    try {
      // 简单解析JWT token（不验证签名）
      const base64Url = token.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const payload = JSON.parse(window.atob(base64))
      return payload.id || payload.userId || payload.sub || null
    } catch (e) {
      console.error('解析token失败:', e)
    }
  }
  
  return null
}

// 获取知识库列表
const fetchKnowledgeBaseList = async () => {
  isLoadingKBs.value = true
  try {
    const token = localStorage.getItem('token')
    const userId = getUserId()
    
    // 添加用户ID参数，确保只获取当前用户的知识库
    const response = await axios.get(`/knowledge/list${userId ? `?user_id=${userId}` : ''}`, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
        'X-User-ID': userId || '' // 在请求头中也传递用户ID
      }
    })
    
    if (response.data && response.data.kb_list) {
      knowledgeBaseList.value = response.data.kb_list
      console.log('知识库列表获取成功:', knowledgeBaseList.value.length)
      
      // 如果存在当前选中的知识库，验证它是否在列表中
      if (currentKbId.value) {
        const exists = knowledgeBaseList.value.some(kb => kb.kb_id === currentKbId.value)
        if (!exists) {
          // 如果当前知识库不属于该用户，重置选择
          resetKnowledgeBase()
          console.warn('当前知识库不属于该用户，已重置选择')
        }
      }
    }
  } catch (error) {
    console.error('获取知识库列表出错:', error)
    showToast('获取知识库列表失败', 'error')
  } finally {
    isLoadingKBs.value = false
  }
}

// 选择知识库
const selectKnowledgeBase = (kbId) => {
  console.log('选择知识库:', kbId)
  currentKbId.value = kbId
  localStorage.setItem('current_kb_id', kbId)
  fetchKnowledgeBaseDetails(kbId)
  
  // 选择知识库后重置对话
  conversation.value = []
}

// 获取知识库详情
const fetchKnowledgeBaseDetails = (kbId) => {
  const kb = knowledgeBaseList.value.find(kb => kb.kb_id === kbId)
  if (kb) {
    selectedKB.value = kb
    taskStatus.value = '知识库已选择，可以开始提问'
    
    // 选择知识库后增加延迟自动显示提问输入框
    setTimeout(() => {
      showQueryInput.value = true
    }, 500)
  } else {
    // 如果在列表中找不到，重新获取知识库列表
    fetchKnowledgeBaseList().then(() => {
      const kb = knowledgeBaseList.value.find(kb => kb.kb_id === kbId)
      if (kb) {
        selectedKB.value = kb
        taskStatus.value = '知识库已选择，可以开始提问'
        setTimeout(() => {
          showQueryInput.value = true
        }, 500)
      } else {
        // 如果仍找不到，可能是知识库已被删除
        resetKnowledgeBase()
        taskStatus.value = '知识库不存在，请选择其他知识库'
      }
    })
  }
}

// 重置知识库选择
const resetKnowledgeBase = () => {
  currentKbId.value = ''
  selectedKB.value = null
  conversation.value = []
  showQueryInput.value = false
  localStorage.removeItem('current_kb_id')
}

// 确认删除知识库
const confirmDeleteKB = (kbId) => {
  if (confirm('确定要删除此知识库吗？删除后无法恢复。')) {
    deleteKnowledgeBase(kbId)
  }
}

// 删除知识库
const deleteKnowledgeBase = async (kbId) => {
  try {
    const token = localStorage.getItem('token')
    const userId = getUserId()
    
    await axios.delete(`/knowledge/delete/${kbId}`, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
        'X-User-ID': userId || '' // 添加用户ID确保权限校验
      },
      params: {
        user_id: userId // 在参数中也传递用户ID
      }
    })
    
    // 从列表中移除被删除的知识库
    knowledgeBaseList.value = knowledgeBaseList.value.filter(kb => kb.kb_id !== kbId)
    
    // 如果删除的是当前选中的知识库，重置选择
    if (currentKbId.value === kbId) {
      resetKnowledgeBase()
    }
    
    showToast('知识库已成功删除', 'success')
  } catch (error) {
    console.error('删除知识库出错:', error)
    showToast('删除知识库失败', 'error')
  }
}

// 格式化日期
const formatDate = (timestamp) => {
  if (!timestamp) return '未知时间'
  
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

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
  processingStage.value = 'uploading'
  taskStatus.value = '文档处理中...'

  const formData = new FormData()
  formData.append('file', currentFile.value)
  
  // 添加用户ID到表单数据
  const userId = getUserId()
  if (userId) {
    formData.append('user_id', userId)
  }

  // 创建取消令牌
  cancelTokenSource.value = axios.CancelToken.source()

  try {
    // 获取token
    const token = localStorage.getItem('token')
    
    const response = await axios.post('/knowledge/process', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': token ? `Bearer ${token}` : '',
        'X-User-ID': userId || '' // 添加用户ID到请求头
      },
      cancelToken: cancelTokenSource.value.token,
      onUploadProgress: (progressEvent) => {
        if (progressEvent.loaded >= progressEvent.total) {
          processingStage.value = 'analyzing'
        }
      }
    })

    if (response.data && response.data.kb_id) {
      currentKbId.value = response.data.kb_id
      localStorage.setItem('current_kb_id', response.data.kb_id)
      taskStatus.value = '处理成功，可以开始提问'
      showQueryInput.value = true  // 自动显示提问输入框
      // 处理成功后刷新知识库列表
      fetchKnowledgeBaseList()
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
    // 获取token和用户ID
    const token = localStorage.getItem('token')
    const userId = getUserId()
    
    // 准备请求数据
    const requestData = {
      query: query,
      stream: true,
      kb_id: currentKbId.value,
      user_id: userId // 添加用户ID确保查询权限
    }
    
    console.log('发送查询请求，知识库ID:', currentKbId.value)
    
    // 发送请求
    const response = await fetch('/api/v1/knowledge/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
        'X-User-ID': userId || '' // 在请求头中也传递用户ID
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

/* 加载动画容器 */
.loading-animation-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: 20px 0;
}

.loading-text {
  color: #a5b4fc;
  font-size: 1.2rem;
  margin-top: 10px;
  text-align: center;
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

.action-section {
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

/* 对话样式 - 更新为Chrome风格 */
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
  padding: 12px 16px;
  border-radius: 8px;
  max-width: 80%;
  animation: fadeIn 0.3s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  margin-bottom: 8px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user {
  background-color: rgba(99, 102, 241, 0.15);
  align-self: flex-end;
  border-radius: 18px 18px 0 18px;
  color: #e0e0ff;
}

.message.assistant {
  background-color: rgba(30, 33, 48, 0.7);
  align-self: flex-start;
  border-radius: 18px 18px 18px 0;
  color: #e0e0ff;
}

.message-content {
  color: #e0e0ff;
  line-height: 1.5;
  font-size: 0.95rem;
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
  
  .action-section,
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
  
  .process-btn, .query-btn {
    min-width: 120px;
    padding: 8px 12px;
    font-size: 0.9rem;
  }
  
  .message {
    padding: 10px;
    max-width: 90%;
  }
  
  .loading-animation-container DotLottieVue {
    height: 200px !important;
    width: 200px !important;
  }
}

/* 新增：知识库列表样式 */
.kb-list-section {
  margin: 30px 0;
  padding: 20px;
  background-color: rgba(30, 33, 48, 0.7);
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.2);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.2);
  padding-bottom: 10px;
}

.section-header h3 {
  font-size: 1.3rem;
  color: #a5b4fc;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.refresh-btn {
  background: none;
  border: none;
  color: #6366f1;
  cursor: pointer;
  padding: 5px;
  border-radius: 50%;
  transition: all 0.3s ease;
}

.refresh-btn:hover {
  background-color: rgba(99, 102, 241, 0.1);
  transform: rotate(30deg);
}

.kb-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 300px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #6366f1 #1e2130;
}

.kb-list::-webkit-scrollbar {
  width: 4px;
}

.kb-list::-webkit-scrollbar-track {
  background: #1e2130;
}

.kb-list::-webkit-scrollbar-thumb {
  background-color: #6366f1;
  border-radius: 2px;
}

.kb-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background-color: rgba(22, 25, 35, 0.7);
  border-radius: 8px;
  border-left: 3px solid #6366f1;
  transition: all 0.3s ease;
  cursor: pointer;
}

.kb-item:hover {
  background-color: rgba(30, 33, 48, 0.9);
  transform: translateX(3px);
}

.kb-details {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.kb-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: rgba(99, 102, 241, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6366f1;
  font-size: 1.2rem;
}

.kb-info {
  flex: 1;
}

.kb-name {
  font-weight: 500;
  color: #e0e0ff;
  margin-bottom: 5px;
  word-break: break-word;
  text-overflow: ellipsis;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 1; /* For modern browsers */
  line-clamp: 1; /* Standard property */
  -webkit-box-orient: vertical;
}

.kb-date {
  font-size: 0.8rem;
  color: #a5b4fc;
}

.kb-actions {
  display: flex;
  gap: 8px;
}

.kb-action-btn {
  background: none;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.kb-action-btn.delete {
  color: #ef4444;
}

.kb-action-btn.delete:hover {
  background-color: rgba(239, 68, 68, 0.1);
}

.kb-empty-state, .kb-loading {
  padding: 30px 20px;
  text-align: center;
  color: #a5b4fc;
}

.kb-empty-state i, .kb-loading i {
  font-size: 2rem;
  margin-bottom: 10px;
  display: block;
}

.kb-loading i {
  color: #6366f1;
}

/* 选中的知识库信息样式 */
.selected-kb-info {
  margin: 20px 0;
  padding: 20px;
  background-color: rgba(30, 33, 48, 0.7);
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.2);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.kb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.kb-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.kb-title i {
  color: #6366f1;
  font-size: 1.2rem;
}

.kb-title h3 {
  color: #e0e0ff;
  font-size: 1.2rem;
  font-weight: 500;
  margin: 0;
}

.kb-description {
  color: #a5b4fc;
  font-size: 0.95rem;
  line-height: 1.5;
}

.kb-back-btn {
  background-color: rgba(99, 102, 241, 0.1);
  color: #6366f1;
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.kb-back-btn:hover {
  background-color: rgba(99, 102, 241, 0.2);
}

.kb-item.kb-selected {
  background-color: rgba(99, 102, 241, 0.2);
  border-left: 3px solid #10b981;
}

.kb-action-btn.query {
  color: #10b981;
}

.kb-action-btn.query:hover {
  background-color: rgba(16, 185, 129, 0.1);
}

/* 返回按钮样式 */
.header-with-back {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.back-btn {
  background-color: rgba(99, 102, 241, 0.1);
  color: #6366f1;
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background-color: rgba(99, 102, 241, 0.2);
}

.header-with-back h3 {
  color: #e0e0ff;
  font-size: 1.2rem;
  font-weight: 500;
  margin: 0;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style> 