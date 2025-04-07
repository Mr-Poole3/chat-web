<template>
  <div class="container">
    <!-- 侧边栏遮罩 (移动设备) -->
    <div class="sidebar-overlay" :class="{ active: sidebarExpanded }" @click="toggleSidebar"></div>
    
    <!-- 侧边栏 -->
    <SideBar 
      :expanded="sidebarExpanded"
      :activeToolId="activeToolId"
      @load-chat-tool="loadChatTool"
      @load-tool="loadTool"
    />

    <!-- 主内容区 -->
    <div class="main-content">
      <div id="ai-chat-page">
        <!-- 顶部 header -->
        <ChatHeader 
          :selectedModel="selectedModel"
          :availableModels="availableModels"
          :loading="loading"
          :username="username"
          @logout="handleLogout"
          @change-model="selectedModel = $event"
        />

        <!-- 聊天内容区 -->
        <ChatMessages 
          ref="messagesContainer"
          :messages="messages"
          :renderMarkdown="renderMarkdown"
        />

        <!-- 底部输入区 -->
        <InputComponent 
          :inputMessage="inputMessage"
          :loading="loading"
          @update:inputMessage="inputMessage = $event"
          @send-message="sendMessage"
          @new-chat="createNewChat"
          @new-line="newline"
        />
      </div>
      
      <!-- 工具页面（初始隐藏） -->
      <ToolPages :tools="tools" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import axios from 'axios'
import { DotLottieVue } from '@lottiefiles/dotlottie-vue'

/**
 * 流式响应处理逻辑:
 * 1. 使用fetch API和ReadableStream处理服务器发送的事件(SSE)
 * 2. 实时解析并显示LLM的回复，支持DeepSeek和Azure模型
 * 3. 在消息流式传输过程中展示打字指示器和已收到的内容
 * 4. 处理流式传输结束后的状态更新
 * 5. 支持思考过程的展示
 */

// 导入拆分的组件
import SideBar from '@/components/chat/SideBar.vue'
import ChatHeader from '@/components/chat/ChatHeader.vue'
import ChatMessages from '@/components/chat/ChatMessages.vue'
import InputComponent from '@/components/chat/InputComponent.vue'
import ToolPages from '@/components/chat/ToolPages.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 可选模型列表
const availableModels = [
  { id: 'DeepSeek-R1', name: 'DeepSeek-R1' },
  { id: 'DeepSeek-V3', name: 'DeepSeek-V3' },
  { id: 'gpt-4o-mini', name: 'GPT-4o-mini' },
  { id: 'gpt-4o', name: 'GPT-4o' },
]

// 工具列表
const tools = [
  {
    id: 'pdf-to-word',
    title: 'PDF 转换器',
    description: '把你的PDF转为任意格式的文档',
    icon: 'fas fa-file-pdf'
  },
  {
    id: 'essay',
    title: '论文辅助阅读',
    description: '智能辅助论文阅读和分析',
    icon: 'fas fa-pen-fancy'
  },
  {
    id: 'ppt',
    title: 'Open Manus',
    description: '开发中，敬请期待',
    icon: 'fas fa-file-powerpoint'
  },
  {
    id: 'resume',
    title: '简历生成器',
    description: '一键生成专业简历',
    icon: 'fas fa-file-alt'
  },
  {
    id: 'flowchart',
    title: '流程图生成器',
    description: '快速创建精美流程图',
    icon: 'fas fa-project-diagram'
  }
]

const features = {
  chat: {
    id: 'chat',
    icon: 'fas fa-robot',
    title: 'AI 聊天',
    description: '与智能 AI 助手进行自然对话，获取帮助和建议。'
  },
  pdf: {
    id: 'pdf',
    icon: 'fas fa-file-pdf',
    title: 'PDF 转换',
    description: '将 PDF 文件转换为其他格式，支持多种文档类型。'
  },
  paper: {
    id: 'paper',
    icon: 'fas fa-pen-fancy',
    title: '论文写作',
    description: '智能辅助论文写作，提供写作建议和格式规范。'
  },
  resume: {
    id: 'resume',
    icon: 'fas fa-file-alt',
    title: '简历生成',
    description: '一键生成专业简历。'
  }
}

const currentFeature = computed(() => features[route.query.feature] || features.chat)
const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
const messagesContainer = ref(null)
const selectedModel = ref('DeepSeek-R1') // 默认选择DeepSeek-R1模型
const username = ref('')
const activeToolId = ref('chat') // 当前活跃的工具ID
const sidebarExpanded = ref(false) // 侧边栏是否展开
const animationCompleted = ref(false) // 动画是否已完成

// 添加聊天会话相关变量
let isFirstMessage = true
let currentChatId = null
const chatSessions = ref([])

// 添加SSE相关的变量
const eventSource = ref(null)
const waitingForResponse = ref(false)
const currentAssistantMessage = ref('')

const renderMarkdown = (content) => {
  if (content === null || content === undefined) {
    return '';
  }
  
  // 处理思考过程（如果有）
  if (content.includes('<think>') || content.includes('</think>')) {
    let thoughtProcess = '';
    let actualResponse = '';
    
    // 处理可能缺少开始标签的情况
    if (!content.includes('<think>') && content.includes('</think>')) {
      const parts = content.split('</think>');
      thoughtProcess = parts[0] || '';
      actualResponse = parts[1] || '';
    } else {
      const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/);
      thoughtProcess = thinkMatch ? thinkMatch[1] : '';
      actualResponse = content.replace(/<think>[\s\S]*?<\/think>/, '');
    }
    
    // 创建思考内容的展示
    let processedContent = '';
    if (thoughtProcess) {
      processedContent += `<div class="thinking-content">
          <details>
              <summary>思考过程</summary>
              <div><pre>${thoughtProcess}</pre></div> 
          </details>
      </div>`;
    }
    
    // 添加实际回答内容，不使用markdown解析
    if (actualResponse) {
      processedContent += `<div class="response-container">${actualResponse}</div>`;
    }
    
    return processedContent;
  }
  
  // 如果没有思考过程标记，直接展示内容
  return `<div class="response-container">${content}</div>`;
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value?.$el) {
    messagesContainer.value.$el.scrollTop = messagesContainer.value.$el.scrollHeight
  }
}

// 关闭SSE连接的方法
const closeEventSource = () => {
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
}

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return

  const userMessage = inputMessage.value.trim()
  messages.value.push({
    role: 'user',
    content: userMessage
  })
  inputMessage.value = ''
  loading.value = true
  waitingForResponse.value = true
  currentAssistantMessage.value = ''
  await scrollToBottom()

  try {
    // 关闭可能存在的之前的连接
    closeEventSource()

    // 添加一个临时的助手消息来显示流式响应
    messages.value.push({
      role: 'assistant',
      content: '',
      streaming: true
    })

    // 使用fetch API请求流式响应
    const response = await fetch('/api/v1/tools/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: selectedModel.value,
        prompt: userMessage,
        max_tokens: 8000,
        temperature: 0.7,
        stream: true,
        feature: currentFeature.value.id
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // 创建一个Reader来读取流数据
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    // 获取最后一条消息的索引用于更新
    const lastIndex = messages.value.length - 1;
    
    // 读取流数据并实时更新UI
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        // 标记消息流已结束
        if (lastIndex >= 0 && messages.value[lastIndex].role === 'assistant') {
          messages.value[lastIndex].streaming = false;
        }
        break;
      }
      
      // 解码二进制数据
      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;
      
      // 处理buffer中的SSE数据（可能包含多个data:行）
      let processedBuffer = '';
      const lines = buffer.split('\n');
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        if (line.startsWith('data: ')) {
          try {
            // 提取data:后面的JSON内容
            const dataContent = line.substring(6).trim();
            
            // 跳过[DONE]标记
            if (dataContent === '[DONE]') continue;
            
            // 解析并处理不同模型的输出格式
            if (dataContent.startsWith('{')) {
              const jsonData = JSON.parse(dataContent);
              
              // 从DeepSeek或Azure的响应中提取内容
              if (jsonData.choices && jsonData.choices[0].delta && jsonData.choices[0].delta.content) {
                const content = jsonData.choices[0].delta.content;
                if (content !== null) {
                  // 将内容添加到当前助手消息
                  if (lastIndex >= 0 && messages.value[lastIndex].role === 'assistant') {
                    messages.value[lastIndex].content += content;
                  }
                }
              }
            } else {
              // 如果不是JSON，直接将内容添加到消息中
              if (lastIndex >= 0 && messages.value[lastIndex].role === 'assistant') {
                messages.value[lastIndex].content += dataContent;
              }
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e, line);
          }
        }
      }
      
      // 保留未处理完的部分（可能是不完整的行）
      const lastLineIndex = lines.length - 1;
      buffer = lines[lastLineIndex].startsWith('data: ') ? lines[lastLineIndex] : '';
      
      // 滚动到底部以显示最新消息
      await scrollToBottom();
    }

    loading.value = false;
    waitingForResponse.value = false;
    await scrollToBottom();
  } catch (error) {
    console.error('Error in chat request:', error);

    // 更新最后一条消息为错误信息
    const lastIndex = messages.value.length - 1;
    if (lastIndex >= 0 && messages.value[lastIndex].role === 'assistant') {
      messages.value[lastIndex].content = '抱歉，发生了错误，请稍后重试。';
      messages.value[lastIndex].streaming = false;
    }

    // 重置状态
    loading.value = false;
    waitingForResponse.value = false;
    await scrollToBottom();
  }
}

const newline = (e) => {
  const start = e.target.selectionStart
  const end = e.target.selectionEnd
  inputMessage.value = inputMessage.value.substring(0, start) + '\n' + inputMessage.value.substring(end)
  nextTick(() => {
    e.target.selectionStart = e.target.selectionEnd = start + 1
  })
}

// 新建聊天功能
const createNewChat = () => {
  // 重置消息
  messages.value = [];
  isFirstMessage = true;
  
  // 重置动画状态
  animationCompleted.value = false;
  
  // 生成新的会话ID
  currentChatId = Date.now().toString();
  
  // 添加到会话列表
  chatSessions.value.unshift({
    id: currentChatId,
    title: "新对话",
    messages: []
  });
}

// 登出功能
const handleLogout = () => {
  localStorage.removeItem('token');
  router.push('/login');
}

// 工具加载功能
const loadTool = (toolId) => {
  // 隐藏AI聊天页面
  document.getElementById('ai-chat-page').style.display = 'none';
  
  // 隐藏所有工具页面
  document.querySelectorAll('.tool-page').forEach(page => {
    page.style.display = 'none';
  });
  
  // 显示选定的工具页面
  const selectedToolPage = document.getElementById(`${toolId}-page`);
  if (selectedToolPage) {
    selectedToolPage.style.display = 'block';
  }
  
  // 更新活跃工具ID
  activeToolId.value = toolId;
  
  // 在移动设备上自动关闭侧边栏
  if (window.innerWidth <= 768) {
    sidebarExpanded.value = false;
  }
}

// 返回聊天功能
const loadChatTool = () => {
  // 显示AI聊天页面
  document.getElementById('ai-chat-page').style.display = 'flex';
  
  // 隐藏所有工具页面
  document.querySelectorAll('.tool-page').forEach(page => {
    page.style.display = 'none';
  });
  
  // 更新活跃工具ID
  activeToolId.value = 'chat';
  
  // 在移动设备上自动关闭侧边栏
  if (window.innerWidth <= 768) {
    sidebarExpanded.value = false;
  }
}

// 加载用户信息
const loadUserInfo = () => {
  const token = localStorage.getItem('token');
  if (!token) {
    router.push('/login');
    return;
  }
  
  // 验证token并获取用户信息
  axios.get('/auth/me', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })
  .then(response => {
    if (response.data && response.data.username) {
      username.value = response.data.username;
    }
  })
  .catch(error => {
    console.error('Error loading user info:', error);
    localStorage.removeItem('token');
    router.push('/login');
  });
}

// 侧边栏切换功能
const toggleSidebar = () => {
  sidebarExpanded.value = !sidebarExpanded.value;
}

// 处理动画完成事件
const handleAnimationComplete = () => {
  animationCompleted.value = true;
  // 保持在最后一帧
  nextTick(() => {
    const lottieElement = document.querySelector('.welcome-animation');
    if (lottieElement) {
      // 设置为140帧，即动画的最后一帧
      lottieElement.setFrame(140);
    }
  });
}

// 在组件卸载时关闭SSE连接
onUnmounted(() => {
  closeEventSource()
})

onMounted(() => {
  loadUserInfo();
  loadChatTool(); // 默认加载聊天工具
  
  // 初始化动画状态
  animationCompleted.value = false;
  
  // 自动调整文本框高度
  const userInputElement = document.getElementById('user-input');
  if (userInputElement) {
    userInputElement.addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = (this.scrollHeight) + 'px';
    });
  }
});

watch(messages, scrollToBottom, { deep: true })
</script>

<style>
@import '@/assets/styles/chat.css';
</style>