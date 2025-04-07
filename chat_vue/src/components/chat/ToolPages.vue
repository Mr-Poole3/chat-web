<template>
  <div>
    <div v-for="tool in tools" :key="tool.id" :id="`${tool.id}-page`" class="tool-page" style="display: none;">
      <!-- 简历生成器页面 -->
      <iframe v-if="tool.id === 'resume'" src="http://139.224.203.197:7864/app/dashboard/resumes" class="tool-iframe"></iframe>
      
      <!-- 论文辅助阅读页面 -->
      <iframe v-else-if="tool.id === 'essay'" src="http://139.224.203.197:7863/" class="tool-iframe"></iframe>
      
      <!-- 其他工具页面显示标题和描述 -->
      <template v-else>
        <h2>{{ tool.title }}</h2>
        <p>{{ tool.description }}</p>
      </template>
    </div>
  </div>
</template>

<script setup>
defineProps({
  tools: {
    type: Array,
    required: true
  }
})
</script> 