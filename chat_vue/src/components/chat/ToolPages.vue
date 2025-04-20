<template>
  <div class="tool-pages-container">
    <div v-for="tool in tools" :key="tool.id" :id="`${tool.id}-page`" class="tool-page" style="display: none;">
      <!-- 移动端菜单按钮 -->
      <div class="mobile-menu-button" @click="toggleSidebar">
        <i class="fas fa-bars"></i>
      </div>
      
      <!-- 知识库工具页面 -->
      <KnowledgeBaseTool v-if="tool.id === 'pdf-to-word'" />
      
      <!-- AI知识库工具页面 -->
      <KnowledgeBaseTool v-else-if="tool.id === 'knowledge-base'" />
      
      <!-- 简历生成器页面 -->
      <iframe v-else-if="tool.id === 'resume'" src="http://139.224.203.197:7864/app/dashboard/resumes" class="tool-iframe"></iframe>
      
      <!-- 论文辅助阅读页面 -->
      <iframe v-else-if="tool.id === 'essay'" src="http://139.224.203.197:7863/" class="tool-iframe"></iframe>
      
      <!-- 流程图生成器页面 -->
      <iframe v-else-if="tool.id === 'flowchart'" src="http://139.224.203.197:7865/" class="tool-iframe"></iframe>
      
      <!-- Open Manus页面 -->
      <iframe v-else-if="tool.id === 'ppt'" src="http://139.224.203.197:7862/" class="tool-iframe"></iframe>
      
      <!-- 其他工具页面显示标题和描述 -->
      <template v-else>
        <h2>{{ tool.title }}</h2>
        <p>{{ tool.description }}</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'
import KnowledgeBaseTool from './KnowledgeBaseTool.vue'

defineProps({
  tools: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['toggle-sidebar'])

const toggleSidebar = () => {
  emit('toggle-sidebar')
}
</script>

<style scoped>
.tool-pages-container {
  width: 100%;
  height: 100%;
}

.tool-page {
  width: 100%;
  height: 100%;
  position: relative;
}

.tool-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.mobile-menu-button {
  display: none;
  position: absolute;
  top: 15px;
  left: 15px;
  color: #6366f1;
  font-size: 20px;
  cursor: pointer;
  z-index: 10;
  width: 40px;
  height: 40px;
  background: rgba(30, 33, 48, 0.8);
  border-radius: 8px;
  border: 1px solid rgba(99, 102, 241, 0.3);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(5px);
}

@media (max-width: 768px) {
  .mobile-menu-button {
    display: flex;
  }
}
</style> 