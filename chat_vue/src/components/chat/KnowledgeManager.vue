<template>
  <div class="knowledge-manager">
    <div class="tabs-container">
      <div 
        class="tab" 
        :class="{ active: activeTab === 'upload' }"
        @click="switchTab('upload')"
      >
        <i class="fas fa-cloud-upload-alt"></i>
        <span>文档上传</span>
      </div>
      <div 
        class="tab" 
        :class="{ active: activeTab === 'list' }"
        @click="switchTab('list')"
      >
        <i class="fas fa-database"></i>
        <span>知识库列表</span>
      </div>
      <div 
        class="tab" 
        :class="{ active: activeTab === 'query' }"
        @click="switchTab('query')"
      >
        <i class="fas fa-question-circle"></i>
        <span>知识问答</span>
      </div>
    </div>
    
    <div class="content-container">
      <transition name="fade" mode="out-in">
        <KnowledgeBaseTool v-if="activeTab === 'upload'" />
        <KnowledgeList v-else-if="activeTab === 'list'" />
        <KnowledgeQuery v-else />
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import KnowledgeBaseTool from './KnowledgeBaseTool.vue'
import KnowledgeQuery from './KnowledgeQuery.vue'
import KnowledgeList from './KnowledgeList.vue'

const activeTab = ref('upload')

// 切换标签
const switchTab = (tab) => {
  activeTab.value = tab
}

// 监听事件以在组件间切换
const handleSwitchToQuery = (event) => {
  activeTab.value = 'query'
}

onMounted(() => {
  // 添加事件监听器
  window.addEventListener('switch-to-query', handleSwitchToQuery)

  // 如果已存在知识库ID，默认显示问答页面
  if (localStorage.getItem('current_kb_id')) {
    activeTab.value = 'query'
  }
})

onUnmounted(() => {
  // 移除事件监听器
  window.removeEventListener('switch-to-query', handleSwitchToQuery)
})
</script>

<style scoped>
.knowledge-manager {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #161923;
  color: #e0e0ff;
}

.tabs-container {
  display: flex;
  border-bottom: 1px solid rgba(99, 102, 241, 0.2);
  padding: 0 20px;
  background-color: rgba(22, 25, 35, 0.8);
}

.tab {
  padding: 15px 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  color: #9f9fb8;
  position: relative;
  transition: all 0.2s;
}

.tab i {
  margin-right: 8px;
  font-size: 1rem;
}

.tab:hover {
  color: #e0e0ff;
}

.tab.active {
  color: #6366f1;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 10%;
  width: 80%;
  height: 3px;
  background-color: #6366f1;
  border-radius: 3px 3px 0 0;
}

.content-container {
  flex: 1;
  overflow: hidden;
}

/* 淡入淡出过渡效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .tabs-container {
    padding: 0 10px;
  }
  
  .tab {
    padding: 12px 15px;
    font-size: 0.9rem;
  }
  
  .tab i {
    font-size: 1rem;
  }
}
</style> 