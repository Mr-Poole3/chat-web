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
        <span>天汇AI</span>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'pdf-to-word' }" 
        @click="$emit('load-tool', 'pdf-to-word')"
      >
        <img src="https://img.icons8.com/?size=100&id=47812&format=png&color=FFFFFF" alt="PDF to Word">
        <span>PDF 转换器</span>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'essay' }" 
        @click="$emit('load-tool', 'essay')"
      >
        <img src="https://img.icons8.com/?size=100&id=42763&format=png&color=FFFFFF" alt="论文">
        <span>论文辅助阅读</span>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'ppt' }" 
        @click="$emit('load-tool', 'ppt')"
      >
        <img src="https://img.icons8.com/?size=100&id=saSupsgVcmJe&format=png&color=FFFFFF" alt="PPT"/>
        <span>Open Manus</span>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'resume' }" 
        @click="$emit('load-tool', 'resume')"
      >
        <img src="https://img.icons8.com/?size=100&id=23877&format=png&color=FFFFFF" alt="简历">
        <span>简历生成器</span>
      </div>
      <div 
        class="tool-item" 
        :class="{ active: activeToolId === 'flowchart' }" 
        @click="$emit('load-tool', 'flowchart')"
      >
        <img src="https://img.icons8.com/?size=100&id=1763&format=png&color=FFFFFF" alt="流程图">
        <span>流程图生成器</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

defineProps({
  expanded: {
    type: Boolean,
    default: false
  },
  activeToolId: {
    type: String,
    default: 'chat'
  }
})

defineEmits(['load-chat-tool', 'load-tool'])

const navigateTo = (path) => {
  router.push(path)
}
</script> 