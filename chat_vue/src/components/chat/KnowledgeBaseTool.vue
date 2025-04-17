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
    </div>

    <div class="processing-section" v-if="currentFile">
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
        <button @click="clearResults" v-if="!processing && results.length > 0" class="clear-btn">
          <i class="fas fa-trash"></i>
          清除结果
        </button>
      </div>
    </div>

    <div class="results-section" v-if="results.length > 0">
      <h3>处理结果</h3>
      <div class="results-content">
        <div v-for="(result, index) in results" :key="index" class="result-item">
          <div class="result-header">
            <span class="result-type">
              <i class="fas" :class="getTypeIcon(result.type)"></i>
              {{ getTypeName(result.type) }}
            </span>
            <span class="result-confidence" :class="confidenceClass(result.confidence)">
              置信度: {{ result.confidence }}%
            </span>
          </div>
          <div class="result-text">{{ result.text }}</div>
          <div class="result-actions">
            <button @click="copyResultText(result.text)" class="action-btn">
              <i class="fas fa-copy"></i> 复制
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="empty-state" v-if="!currentFile && !processing && results.length === 0">
      <i class="fas fa-file-alt empty-icon"></i>
      <p>上传文档开始提取知识</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'

const fileInput = ref(null)
const isDragging = ref(false)
const currentFile = ref(null)
const processing = ref(false)
const progress = ref(0)
const results = ref([])
const taskStatus = ref('')
const processingStage = ref('')
const cancelTokenSource = ref(null)

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

    if (response.data && response.data.results) {
      results.value = response.data.results
      taskStatus.value = '处理成功'
      progress.value = 100
    } else {
      // 如果没有返回预期的结果格式，设置一个默认的结果
      results.value = [
        {
          type: '文档分析',
          confidence: 90,
          text: '文档处理完成，但未返回详细分析结果。'
        }
      ]
      taskStatus.value = '处理完成，结果有限'
    }
  } catch (error) {
    console.error('处理文件时出错:', error)
    
    if (axios.isCancel(error)) {
      taskStatus.value = '处理已取消'
      showToast('文档处理已取消')
    } else {
      taskStatus.value = '处理失败'
      showToast('处理文件时出错，请重试', 'error')
      results.value = [
        {
          type: '错误',
          confidence: 0,
          text: `处理失败: ${error.response?.data?.detail || error.message || '未知错误'}`
        }
      ]
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

const clearResults = () => {
  results.value = []
  taskStatus.value = ''
  progress.value = 0
}

const copyResultText = (text) => {
  navigator.clipboard.writeText(text)
    .then(() => showToast('已复制到剪贴板'))
    .catch(err => showToast('复制失败: ' + err, 'error'))
}

const confidenceClass = (confidence) => {
  if (confidence >= 80) return 'confidence-high'
  if (confidence >= 50) return 'confidence-medium'
  return 'confidence-low'
}

const getTypeIcon = (type) => {
  switch (type) {
    case 'ENTITY': return 'fa-tag'
    case 'RELATION': return 'fa-network-wired'
    case 'CONTEXT': return 'fa-file-alt'
    default: return 'fa-file-alt'
  }
}

const getTypeName = (type) => {
  switch (type) {
    case 'ENTITY': return '实体'
    case 'RELATION': return '关系'
    case 'CONTEXT': return '上下文'
    default: return '其他'
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

.clear-btn {
  background-color: #6c757d;
  color: white;
}

.clear-btn:hover {
  background-color: #5a6268;
  transform: translateY(-2px);
  box-shadow: 0 2px 5px rgba(108, 117, 125, 0.3);
}

.action-btn {
  background-color: #2d3748;
  color: #a5b4fc;
  font-size: 0.9em;
  min-width: auto;
  padding: 4px 12px;
}

.action-btn:hover {
  background-color: #4a5568;
  color: #e0e0ff;
}

.results-section {
  margin-top: 30px;
}

.results-section h3 {
  color: #e0e0ff;
  margin-bottom: 20px;
  font-size: 1.3rem;
  position: relative;
  padding-bottom: 10px;
}

.results-section h3::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: 0;
  width: 60px;
  height: 3px;
  background-color: #6366f1;
  border-radius: 3px;
}

.results-content {
  display: grid;
  gap: 15px;
}

.result-item {
  background-color: rgba(30, 33, 48, 0.7);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 8px;
  padding: 15px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.result-item:hover {
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
  border-color: rgba(99, 102, 241, 0.4);
  transform: translateY(-2px);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 10px;
}

.result-type {
  font-weight: bold;
  color: #6366f1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-confidence {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8em;
}

.confidence-high {
  background-color: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.confidence-medium {
  background-color: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.confidence-low {
  background-color: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.result-text {
  color: #e0e0ff;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
  padding-right: 5px;
  font-size: 0.95rem;
  scrollbar-width: thin;
  scrollbar-color: #6366f1 #1e2130;
}

.result-text::-webkit-scrollbar {
  width: 4px;
}

.result-text::-webkit-scrollbar-track {
  background: #1e2130;
}

.result-text::-webkit-scrollbar-thumb {
  background-color: #6366f1;
  border-radius: 2px;
}

.result-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
  gap: 8px;
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
  
  .processing-section {
    padding: 15px;
  }
  
  .file-name {
    font-size: 0.9rem;
    max-width: 200px;
  }
  
  .action-buttons {
    justify-content: center;
  }
  
  .process-btn, .cancel-btn, .clear-btn {
    min-width: 120px;
    padding: 8px 12px;
    font-size: 0.9rem;
  }
  
  .result-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .result-text {
    font-size: 0.9rem;
    max-height: 200px;
  }
}
</style> 