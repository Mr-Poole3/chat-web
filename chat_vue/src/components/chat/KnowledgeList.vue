<template>
  <div class="knowledge-list">
    <div class="list-header">
      <h2>我的知识库</h2>
      <p class="description">已上传的文档库，可以选择进行问答或删除</p>
    </div>

    <div v-if="loading" class="loading-container">
      <i class="fas fa-spinner fa-spin"></i>
      <p>加载知识库列表中...</p>
    </div>

    <div v-else-if="knowledgeBases.length === 0" class="empty-state">
      <i class="fas fa-database empty-icon"></i>
      <p>暂无知识库，请先上传文档</p>
    </div>

    <div v-else class="kb-list">
      <div v-for="kb in knowledgeBases" :key="kb.kb_id" class="kb-item">
        <div class="kb-info">
          <div class="kb-name">
            <i class="fas fa-file-alt"></i>
            <span>{{ kb.file_name || '未命名文档' }}</span>
          </div>
          <div class="kb-meta">
            <span class="kb-id">ID: {{ formatKbId(kb.kb_id) }}</span>
            <span class="kb-date">{{ formatDate(kb.create_time) }}</span>
          </div>
        </div>
        <div class="kb-actions">
          <button class="action-btn select-btn" @click="selectKnowledgeBase(kb)" title="选择此知识库">
            <i class="fas fa-check-circle"></i>
            选择
          </button>
          <button class="action-btn delete-btn" @click="confirmDelete(kb)" title="删除此知识库">
            <i class="fas fa-trash-alt"></i>
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div v-if="showDeleteModal" class="delete-modal">
      <div class="modal-content">
        <h3>确认删除</h3>
        <p>确定要删除知识库 "{{ selectedKb?.file_name || '未命名文档' }}" 吗？此操作不可撤销。</p>
        <div class="modal-actions">
          <button class="cancel-btn" @click="showDeleteModal = false">取消</button>
          <button class="confirm-btn" @click="deleteKnowledgeBase" :disabled="deleting">
            <i class="fas" :class="deleting ? 'fa-spinner fa-spin' : 'fa-trash-alt'"></i>
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const knowledgeBases = ref([])
const loading = ref(true)
const showDeleteModal = ref(false)
const selectedKb = ref(null)
const deleting = ref(false)

// 加载知识库列表
const loadKnowledgeBases = async () => {
  loading.value = true
  try {
    // 获取token
    const token = localStorage.getItem('token')
    
    const response = await axios.get('/knowledge/list', {
      headers: {
        'Authorization': token ? `Bearer ${token}` : ''
      }
    })
    
    if (response.data && response.data.kb_list) {
      knowledgeBases.value = response.data.kb_list
    }
  } catch (error) {
    console.error('获取知识库列表失败:', error)
    showToast('获取知识库列表失败', 'error')
  } finally {
    loading.value = false
  }
}

// 选择知识库
const selectKnowledgeBase = (kb) => {
  localStorage.setItem('current_kb_id', kb.kb_id)
  showToast(`已选择知识库: ${kb.file_name || '未命名文档'}`, 'success')
  
  // 触发事件以切换到问答页面
  window.dispatchEvent(new CustomEvent('switch-to-query'))
}

// 确认删除
const confirmDelete = (kb) => {
  selectedKb.value = kb
  showDeleteModal.value = true
}

// 删除知识库
const deleteKnowledgeBase = async () => {
  if (!selectedKb.value || deleting.value) return
  
  deleting.value = true
  try {
    // 获取token
    const token = localStorage.getItem('token')
    
    await axios.delete(`/knowledge/delete/${selectedKb.value.kb_id}`, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : ''
      }
    })
    
    // 从列表中移除
    knowledgeBases.value = knowledgeBases.value.filter(
      kb => kb.kb_id !== selectedKb.value.kb_id
    )
    
    showToast('知识库已成功删除', 'success')
    
    // 如果删除的是当前选中的知识库，则清除localStorage
    const currentKbId = localStorage.getItem('current_kb_id')
    if (currentKbId === selectedKb.value.kb_id) {
      localStorage.removeItem('current_kb_id')
    }
    
    showDeleteModal.value = false
  } catch (error) {
    console.error('删除知识库失败:', error)
    showToast('删除知识库失败', 'error')
  } finally {
    deleting.value = false
  }
}

// 格式化日期
const formatDate = (timestamp) => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 格式化知识库ID
const formatKbId = (id) => {
  return id.slice(0, 8) + '...'
}

// 简单的提示实现
const showToast = (message, type = 'info') => {
  alert(message)
}

onMounted(() => {
  loadKnowledgeBases()
})
</script>

<style scoped>
.knowledge-list {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow-y: auto;
}

.list-header h2 {
  margin: 0 0 5px 0;
  font-size: 1.8rem;
  color: #e0e0ff;
}

.list-header .description {
  margin: 0 0 20px 0;
  color: #9f9fb8;
  font-size: 0.9rem;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 50px 0;
  color: #9f9fb8;
}

.loading-container i {
  font-size: 2rem;
  margin-bottom: 10px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 50px 0;
  color: #9f9fb8;
}

.empty-state .empty-icon {
  font-size: 3rem;
  margin-bottom: 20px;
  color: #5b5b7b;
}

.kb-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.kb-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background: rgba(30, 34, 45, 0.7);
  border-radius: 8px;
  border-left: 3px solid #6366f1;
  transition: all 0.2s;
}

.kb-item:hover {
  background: rgba(40, 44, 55, 0.8);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.kb-info {
  flex: 1;
}

.kb-name {
  display: flex;
  align-items: center;
  font-weight: 600;
  margin-bottom: 5px;
}

.kb-name i {
  color: #6366f1;
  margin-right: 10px;
}

.kb-meta {
  display: flex;
  font-size: 0.8rem;
  color: #9f9fb8;
}

.kb-id {
  margin-right: 15px;
}

.kb-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  transition: all 0.2s;
}

.action-btn i {
  margin-right: 5px;
}

.select-btn {
  background: #6366f1;
  color: white;
}

.select-btn:hover {
  background: #4f46e5;
}

.delete-btn {
  background: rgba(220, 38, 38, 0.1);
  color: #ef4444;
}

.delete-btn:hover {
  background: rgba(220, 38, 38, 0.2);
}

.delete-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1e222d;
  border-radius: 8px;
  padding: 20px;
  width: 90%;
  max-width: 400px;
}

.modal-content h3 {
  margin-top: 0;
  color: #e0e0ff;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.cancel-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.1);
  color: #e0e0ff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.confirm-btn {
  padding: 8px 16px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.confirm-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.confirm-btn i {
  margin-right: 5px;
}
</style> 