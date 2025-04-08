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
          @toggle-sidebar="toggleSidebar"
        />

        <!-- 聊天内容区 -->
        <ChatMessages 
          ref="messagesContainer"
          :messages="messages"
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

/**
 * 流式响应处理逻辑:
 * 1. 使用fetch API和ReadableStream处理服务器发送的事件(SSE)
 * 2. 实时解析并显示LLM的回复，支持DeepSeek和Azure模型
 * 3. 在消息流式传输过程中展示打字指示器和已收到的内容
 * 4. 处理流式传输结束后的状态更新
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

// 添加聊天会话相关变量
let isFirstMessage = true
let currentChatId = null
const chatSessions = ref([])

// 添加SSE相关的变量
const eventSource = ref(null)
const waitingForResponse = ref(false)
const currentAssistantMessage = ref('')

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
      try {
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
        
        // 处理buffer中的SSE数据
        const lines = buffer.split('\n\n');
        
        // 创建一个新的buffer用于存储未处理完的行
        let newBuffer = '';
        
        // 逐行处理
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          
          if (line.startsWith('data: ')) {
            try {
              // 提取data:后面的内容
              const dataContent = line.substring(6).trim();
              
              // 跳过[DONE]标记
              if (dataContent === '[DONE]') continue;
              
              // 尝试解析JSON
              if (dataContent.startsWith('{')) {
                try {
                  const jsonData = JSON.parse(dataContent);
                  
                  // 处理DeepSeek或Azure风格的响应
                  if (jsonData.choices && 
                      Array.isArray(jsonData.choices) &&
                      jsonData.choices.length > 0 && 
                      jsonData.choices[0].delta && 
                      typeof jsonData.choices[0].delta.content === 'string') {
                    const content = jsonData.choices[0].delta.content;
                    if (content !== null) {
                      // 将内容添加到当前助手消息
                      if (lastIndex >= 0 && 
                          lastIndex < messages.value.length && 
                          messages.value[lastIndex].role === 'assistant') {
                        messages.value[lastIndex].content += content;
                      }
                    }
                  }
                } catch (jsonError) {
                  console.error('解析JSON出错:', jsonError, dataContent);
                  // 如果JSON解析失败但有内容，直接添加原始内容
                  if (dataContent && dataContent !== '[DONE]' && 
                      lastIndex >= 0 && 
                      lastIndex < messages.value.length && 
                      messages.value[lastIndex].role === 'assistant') {
                    messages.value[lastIndex].content += dataContent;
                  }
                }
              } else {
                // 非JSON格式直接添加内容
                if (dataContent && dataContent !== '[DONE]' && 
                    lastIndex >= 0 && 
                    lastIndex < messages.value.length && 
                    messages.value[lastIndex].role === 'assistant') {
                  messages.value[lastIndex].content += dataContent;
                }
              }
            } catch (e) {
              console.error('处理SSE数据时出错:', e, line);
            }
          }
        }
        
        // 保留最后一行（可能不完整）
        newBuffer = lines[lines.length - 1];
        buffer = newBuffer;
        
        // 滚动到底部以显示最新消息
        await scrollToBottom();
      } catch (streamError) {
        console.error('读取流数据时出错:', streamError);
        // 更新最后一条消息以显示错误
        if (lastIndex >= 0 && 
            lastIndex < messages.value.length && 
            messages.value[lastIndex].role === 'assistant') {
          messages.value[lastIndex].content += '\n\n[读取响应时出错，请重试]';
          messages.value[lastIndex].streaming = false;
        }
        break;
      }
    }

    loading.value = false;
    waitingForResponse.value = false;
    await scrollToBottom();
  } catch (error) {
    console.error('聊天请求错误:', error);

    // 更新最后一条消息为错误信息
    const lastIndex = messages.value.length - 1;
    if (lastIndex >= 0 && messages.value[lastIndex].role === 'assistant') {
      messages.value[lastIndex].content = `
抱歉，发生了错误，请稍后重试。

错误详情: ${error.message || '未知错误'}
      `.trim();
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
    selectedToolPage.style.display = 'flex';
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

// 检测窗口大小变化
const handleResize = () => {
  if (window.innerWidth > 768) {
    // 在大屏幕上默认展开侧边栏
    sidebarExpanded.value = false;
  }
}

// 在组件卸载时关闭SSE连接
onUnmounted(() => {
  closeEventSource();
  window.removeEventListener('resize', handleResize);
})

onMounted(() => {
  loadUserInfo();
  loadChatTool(); // 默认加载聊天工具
  
  // 自动调整文本框高度
  const userInputElement = document.getElementById('user-input');
  if (userInputElement) {
    userInputElement.addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = (this.scrollHeight) + 'px';
    });
  }
  
  // 打印环境变量，用于调试
  console.log('环境:', import.meta.env.MODE);
  console.log('API基础URL:', import.meta.env.VITE_API_BASE_URL);
  console.log('WS基础URL:', import.meta.env.VITE_WS_BASE_URL);
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize);
  handleResize(); // 初始调用一次
});

watch(messages, scrollToBottom, { deep: true })
</script>

<style>
@import '@/assets/styles/chat.css';

/* 移动端适配样式 */
@media (max-width: 768px) {
  .container {
    flex-direction: column;
  }
  
  .main-content {
    width: 100%;
  }
  
  .sidebar {
    position: fixed;
    left: -260px;
    top: 0;
    height: 100%;
    z-index: 1000;
    transition: left 0.3s ease;
    width: 260px;
  }
  
  .sidebar.expanded {
    left: 0;
  }
  
  .sidebar-overlay.active {
    display: block;
  }
  
  .message-content {
    max-width: 85%;
  }
  
  .user-message .message-content {
    max-width: 85%;
  }
  
  .bot-message .message-content {
    max-width: 90%;
  }
  
  .header {
    padding: 10px 15px;
  }
  
  .tool-item {
    padding: 12px 15px;
  }
  
  .input-container {
    padding: 15px 10px 10px;
  }
  
  #user-input {
    padding: 12px 45px;
    font-size: 14px;
  }
  
  .tool-iframe {
    width: 100%;
    height: 100%;
    border: none;
  }
}
</style>