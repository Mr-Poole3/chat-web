<template>
  <div class="container">
    <!-- 侧边栏遮罩 (移动设备) -->
    <div class="sidebar-overlay" :class="{ active: sidebarExpanded }" @click="toggleSidebar"></div>
    
    <!-- 侧边栏 -->
    <SideBar 
      :expanded="sidebarExpanded"
      :activeToolId="activeToolId"
      :chatHistory="chatHistory"
      :currentChatId="currentChatId"
      @load-chat-tool="loadChatTool"
      @load-tool="loadTool"
      @new-chat="createNewChat"
      @select-chat="loadChat"
      @delete-chat="deleteChat"
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
          @edit-message="handleEditMessage"
        />

        <!-- 底部输入区 -->
        <InputComponent 
          :inputMessage="inputMessage"
          :loading="loading"
          @update:inputMessage="inputMessage = $event"
          @send-message="sendMessage"
          @new-chat="createNewChat"
          @new-line="newline"
          @stop-generation="stopGeneration"
        />
      </div>
      
      <!-- 工具页面（初始隐藏） -->
      <ToolPages :tools="tools" @toggle-sidebar="toggleSidebar" />
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
    id: 'knowledge-base',
    title: 'AI知识库',
    description: '上传文档，智能提取关键信息，支持多种文档格式',
    icon: 'fas fa-brain'
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
    description: '智能PPT生成和编辑工具',
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
const selectedModel = ref('DeepSeek-R1')
const username = ref('')
const activeToolId = ref('chat')
const sidebarExpanded = ref(false)
const shouldAutoScroll = ref(true)

// 聊天历史记录相关
const chatHistory = ref([])
const currentChatId = ref(null)
const MAX_HISTORY = 15 // 最大历史记录数量

// 添加SSE相关的变量
const eventSource = ref(null)
const waitingForResponse = ref(false)
const currentAssistantMessage = ref('')

// 添加 abortController 变量
const abortController = ref(null)

// 在组件顶部添加标志变量
const hasSavedMessages = ref(false)

const scrollToBottom = async (force = false) => {
  if (!force && !shouldAutoScroll.value) return
  
  await nextTick()
  if (messagesContainer.value?.$el) {
    messagesContainer.value.$el.scrollTop = messagesContainer.value.$el.scrollHeight
  }
}

// 监听滚动事件，判断是否应该自动滚动
const handleScroll = () => {
  if (!messagesContainer.value?.$el) return
  
  const container = messagesContainer.value.$el
  const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 100
  shouldAutoScroll.value = isAtBottom
}

// 关闭SSE连接的方法
const closeEventSource = () => {
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
}

// 从API加载历史记录
const loadChatHistory = async () => {
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      return;
    }

    const response = await axios.get('/chat/history', {
      params: {},
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-User-ID': userStore.userId
      }
    });

    if (response.data && response.data.code === 200) {
      chatHistory.value = response.data.data || [];
    }
  } catch (error) {
  }
}

// 创建新对话
const createNewChat = async () => {
  // 如果正在加载或有流式传输，先停止
  if (loading.value) {
    await stopGeneration();
  }

  // 如果当前有对话，先保存
  if (currentChatId.value && messages.value.length > 0) {
    await saveCurrentChat();
  }
  
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      return;
    }
    
    // 调用API创建新会话
    const response = await axios.post('/chat/sessions', {
      title: '新对话',
      model: selectedModel.value
    }, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-User-ID': userStore.userId
      }
    });
    
    if (response.data && response.data.code === 200) {
      // 设置当前会话ID
      currentChatId.value = response.data.data.id;
      messages.value = [];
      
      // 重新加载聊天历史
      await loadChatHistory();
    }
  } catch (error) {
  }
}

// 保存当前对话
const saveCurrentChat = async () => {
  if (!currentChatId.value || messages.value.length === 0 || hasSavedMessages.value) return;
  
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      return;
    }
    
    // 获取当前对话在历史记录中的位置
    const chatIndex = chatHistory.value.findIndex(chat => chat.id === currentChatId.value);
    
    // 更新会话标题（如果是新对话）
    if (chatIndex === -1 && messages.value.length > 0) {
      const title = messages.value[0]?.content.slice(0, 30) + '...' || '新对话';
      await axios.put(`/chat/sessions/${currentChatId.value}/title`, { title }, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-User-ID': userStore.userId
        }
      });
    }
    
    // 保存最新的聊天消息（只保存上次保存后的新消息）
    const savedMessagesCount = chatIndex !== -1 ? chatHistory.value[chatIndex].messages.length : 0;
    const newMessages = messages.value.slice(savedMessagesCount);
    
    // 添加检查，避免重复保存
    if (newMessages.length === 0) {
      return;
    }
    
    for (let i = 0; i < newMessages.length; i++) {
      const msg = newMessages[i];
      try {
        await axios.post('/chat/messages', {
          session_id: currentChatId.value,
          role: msg.role,
          content: msg.content,
          sequence: savedMessagesCount + i,
          is_terminated: msg.is_terminated || false
        }, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'X-User-ID': userStore.userId
          }
        });
      } catch (error) {
        // 如果是因为is_terminated字段不存在的错误，尝试不带该字段重新保存
        if (error.response?.status === 500) {
          try {
            await axios.post('/chat/messages', {
              session_id: currentChatId.value,
              role: msg.role,
              content: msg.content,
              sequence: savedMessagesCount + i
            }, {
              headers: {
                'Authorization': `Bearer ${token}`,
                'X-User-ID': userStore.userId
              }
            });
          } catch (retryError) {
          }
        }
      }
    }
    
    // 设置保存标志
    hasSavedMessages.value = true;
    
    // 重新加载聊天历史以获取最新状态
    await loadChatHistory();
  } catch (error) {
  }
}

// 加载特定对话
const loadChat = async (chatId) => {
  // 如果正在加载或有流式传输，先停止
  if (loading.value) {
    await stopGeneration();
  }
  
  // 加载选中的对话
  const chat = chatHistory.value.find(c => c.id === chatId);
  if (chat) {
    currentChatId.value = chat.id;
    messages.value = [...chat.messages];
    selectedModel.value = chat.model || 'DeepSeek-R1';
  }
  
  // 在移动设备上自动关闭侧边栏
  if (window.innerWidth <= 768) {
    sidebarExpanded.value = false;
  }
}

// 删除对话
const deleteChat = async (chatId) => {
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      return;
    }
    
    // 如果删除的是当前对话，并且正在加载，先停止生成
    if (chatId === currentChatId.value && loading.value) {
      await stopGeneration();
    }
    
    // 调用API删除对话
    const response = await axios.delete(`/chat/sessions/${chatId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-User-ID': userStore.userId
      }
    });
    
    if (response.data && response.data.code === 200) {
      // 从本地历史记录中移除
      const index = chatHistory.value.findIndex(chat => chat.id === chatId);
      if (index !== -1) {
        // 暂存是否是当前对话
        const isCurrentChat = chatId === currentChatId.value;
        
        // 从历史记录中删除
        chatHistory.value.splice(index, 1);
        
        // 如果删除的是当前对话
        if (isCurrentChat) {
          if (chatHistory.value.length > 0) {
            // 如果还有其他对话，加载第一个对话
            currentChatId.value = chatHistory.value[0].id;
            messages.value = [...chatHistory.value[0].messages];
            selectedModel.value = chatHistory.value[0].model || 'DeepSeek-R1';
          } else {
            // 如果没有其他对话，创建新对话
            await createNewChat();
          }
        }
      }
    }
  } catch (error) {
  }
}

// 修改对话标题
const updateChatTitle = async (chatId, newTitle) => {
  try {
    const token = localStorage.getItem('token');
    if (!token) {
      return;
    }
    
    const response = await axios.put(`/chat/sessions/${chatId}/title`, { title: newTitle }, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'X-User-ID': userStore.userId
      }
    });
    
    if (response.data && response.data.code === 200) {
      // 更新本地历史记录
      const chat = chatHistory.value.find(c => c.id === chatId);
      if (chat) {
        chat.title = newTitle;
      }
    }
  } catch (error) {
  }
}

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return;
  
  const userMessage = inputMessage.value.trim();
  inputMessage.value = '';
  
  // 重置保存标志
  hasSavedMessages.value = false;
  
  // 添加用户消息到消息列表
  messages.value.push({
    role: 'user',
    content: userMessage
  });
  
  // 添加一个临时的助手消息来显示流式响应
  messages.value.push({
    role: 'assistant',
    content: '',
    streaming: true
  });
  
  loading.value = true;
  waitingForResponse.value = true;
  currentAssistantMessage.value = '';
  shouldAutoScroll.value = true;
  await scrollToBottom(true);
  
  // 创建新的 AbortController
  abortController.value = new AbortController();
  
  try {
    // 关闭可能存在的之前的连接
    closeEventSource();

    // 准备请求头
    const headers = {
      'Content-Type': 'application/json',
      'X-User-ID': userStore.userId
    };
    
    // 如果有token，添加到请求头
    const token = localStorage.getItem('token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // 使用fetch API请求流式响应
    const response = await fetch('/api/v1/tools/chat', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
        model: selectedModel.value,
        prompt: userMessage,
        max_tokens: 4096,
        temperature: 0.7,
        stream: true,
        feature: currentFeature.value.id,
        session_id: currentChatId.value
      }),
      signal: abortController.value.signal // 添加 signal
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
            }
          }
        }
        
        // 保留最后一行（可能不完整）
        newBuffer = lines[lines.length - 1];
        buffer = newBuffer;
        
        // 只在启用自动滚动时滚动到底部
        if (shouldAutoScroll.value) {
          await scrollToBottom();
        }
      } catch (streamError) {
        // 更新最后一条消息以显示错误
        if (lastIndex >= 0 && 
            lastIndex < messages.value.length && 
            messages.value[lastIndex].role === 'assistant') {

          messages.value[lastIndex].streaming = false;
        }
        break;
      }
    }

    loading.value = false;
    waitingForResponse.value = false;
    if (shouldAutoScroll.value) {
      await scrollToBottom();
    }

    // 在流式响应完成后保存对话
    await saveCurrentChat();
  } catch (error) {

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
    if (shouldAutoScroll.value) {
      await scrollToBottom();
    }
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

// 登出功能
const handleLogout = () => {
  // 如果正在加载或有流式传输，先停止
  if (loading.value) {
    stopGeneration()
  }
  localStorage.removeItem('token')
  router.push('/login')
}

// 工具加载功能
const loadTool = (toolId) => {
  // 如果正在加载或有流式传输，先停止
  if (loading.value) {
    stopGeneration()
  }

  // 隐藏AI聊天页面
  document.getElementById('ai-chat-page').style.display = 'none'
  
  // 隐藏所有工具页面
  document.querySelectorAll('.tool-page').forEach(page => {
    page.style.display = 'none'
  })
  
  // 显示选定的工具页面
  const selectedToolPage = document.getElementById(`${toolId}-page`)
  if (selectedToolPage) {
    selectedToolPage.style.display = 'flex'
  } else {
    if (toolId === 'pdf-to-word') {
      // 可能需要一种机制来通知 ToolPages 显示这个 slot
      // 或者，将 KnowledgeBaseTool 移出 ToolPages，直接在此处用 v-if 控制
    }
  }
  
  // 更新活跃工具ID
  activeToolId.value = toolId
  
  // 在移动设备上自动关闭侧边栏
  if (window.innerWidth <= 768) {
    sidebarExpanded.value = false
  }
}

// 返回聊天功能
const loadChatTool = () => {
  // 如果正在加载或有流式传输，先停止
  if (loading.value) {
    stopGeneration()
  }

  // 显示AI聊天页面
  document.getElementById('ai-chat-page').style.display = 'flex'
  
  // 隐藏所有工具页面
  document.querySelectorAll('.tool-page').forEach(page => {
    page.style.display = 'none'
  })
  
  // 更新活跃工具ID
  activeToolId.value = 'chat'
  
  // 在移动设备上自动关闭侧边栏
  if (window.innerWidth <= 768) {
    sidebarExpanded.value = false
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
      userStore.setUserId(response.data.id);
      userStore.setUsername(response.data.username);
      // 在获取用户名后加载聊天历史
      loadChatHistory();
    }
  })
  .catch(error => {
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
  // 停止所有生成并清理资源
  if (loading.value) {
    stopGeneration()
  }
  closeEventSource()
  window.removeEventListener('resize', handleResize)
  // 移除滚动事件监听
  if (messagesContainer.value?.$el) {
    messagesContainer.value.$el.removeEventListener('scroll', handleScroll)
  }
})

onMounted(() => {
  loadUserInfo();
  loadChatTool(); // 默认加载聊天工具
  // 注意：loadChatHistory 会在 loadUserInfo 成功获取用户名后调用
  
  // 如果没有历史记录，或者没有当前对话，才创建新对话
  // 这里需要延迟执行，确保 loadChatHistory 已被调用
  setTimeout(() => {
    if (chatHistory.value.length === 0) {
      createNewChat();
    } else {
      // 如果有历史记录，加载最近的一个对话
      currentChatId.value = chatHistory.value[0].id;
      messages.value = [...chatHistory.value[0].messages];
      selectedModel.value = chatHistory.value[0].model || 'DeepSeek-R1';
    }
  }, 100);
  
  // 添加滚动事件监听
  if (messagesContainer.value?.$el) {
    messagesContainer.value.$el.addEventListener('scroll', handleScroll);
  }
  
  // 自动调整文本框高度
  const userInputElement = document.getElementById('user-input');
  if (userInputElement) {
    userInputElement.addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = (this.scrollHeight) + 'px';
    });
  }
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize);
  handleResize(); // 初始调用一次
});

// 处理消息编辑
const handleEditMessage = async ({ index, content }) => {
  // 如果正在加载或流式传输中，不允许编辑
  if (loading.value || messages.value.some(m => m.streaming)) {
    return;
  }

  const originalMessage = messages.value[index];
  if (!originalMessage || originalMessage.role !== 'user') {
    return;
  }

  // 更新消息内容
  messages.value[index].content = content;

  // 删除这条消息之后的所有消息
  messages.value = messages.value.slice(0, index + 1);

  // 重新发送消息以获取新的回复
  loading.value = true;
  waitingForResponse.value = true;
  currentAssistantMessage.value = '';
  shouldAutoScroll.value = true;
  await scrollToBottom(true);

  try {
    // 关闭可能存在的之前的连接
    closeEventSource();

    // 添加一个临时的助手消息来显示流式响应
    messages.value.push({
      role: 'assistant',
      content: '',
      streaming: true
    });

    // 准备请求头
    const headers = {
      'Content-Type': 'application/json',
      'X-User-ID': userStore.userId
    };
    
    // 如果有token，添加到请求头
    const token = localStorage.getItem('token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // 使用fetch API请求流式响应
    const response = await fetch('/api/v1/tools/chat', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
        model: selectedModel.value,
        prompt: content,
        max_tokens: 4096,
        temperature: 0.7,
        stream: true,
        feature: currentFeature.value.id,
        session_id: currentChatId.value
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
            }
          }
        }
        
        // 保留最后一行（可能不完整）
        newBuffer = lines[lines.length - 1];
        buffer = newBuffer;
        
        // 只在启用自动滚动时滚动到底部
        if (shouldAutoScroll.value) {
          await scrollToBottom();
        }
      } catch (streamError) {
        // 更新最后一条消息以显示错误
        if (lastIndex >= 0 && 
            lastIndex < messages.value.length && 
            messages.value[lastIndex].role === 'assistant') {

          messages.value[lastIndex].streaming = false;
        }
        break;
      }
    }

    loading.value = false;
    waitingForResponse.value = false;
    if (shouldAutoScroll.value) {
      await scrollToBottom();
    }

    // 保存对话
    await saveCurrentChat();
  } catch (error) {

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
    if (shouldAutoScroll.value) {
      await scrollToBottom();
    }
  }
}

// 添加停止生成的方法
const stopGeneration = async () => {
  if (abortController.value) {
    abortController.value.abort();
    abortController.value = null;
  }
  
  // 关闭可能存在的之前的连接
  closeEventSource();
  
  loading.value = false;
  waitingForResponse.value = false;
  
  // 更新最后一条消息的状态
  const lastIndex = messages.value.length - 1;
  if (lastIndex >= 0 && messages.value[lastIndex].role === 'assistant') {
    messages.value[lastIndex].streaming = false;
    
    // 只有在有内容时才添加[已停止生成]标记
    if (messages.value[lastIndex].content.trim()) {
      messages.value[lastIndex].content += '\n\n[已停止生成]';
      messages.value[lastIndex].is_terminated = true;
      
      // 不再在这里设置标志和保存消息
      // 让流式输出完全结束后再保存
    } else {
      // 如果没有内容，直接移除这条消息
      messages.value.pop();
    }
  }
}
</script>

<style>
@import '@/assets/styles/chat.css';

/* 容器基础样式 */
.container {
  display: flex;
  height: 100vh;
  width: 100%;
  overflow: hidden;
  position: fixed;
  top: 0;
  left: 0;
}

/* 侧边栏基础样式 */
.sidebar {
  width: 260px;
  min-width: 260px;
  background-color: #161923;
  border-right: 1px solid rgba(99, 102, 241, 0.2);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding-bottom: 20px;
  box-shadow: 0 0 20px rgba(76, 78, 229, 0.1);
  height: 100vh;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 1000;
}

/* 工具项样式 */
.tool-item {
  cursor: pointer;
  transition: all 0.3s ease;
}

.tool-item:hover {
  background-color: rgba(99, 102, 241, 0.1);
}

.tool-item.active {
  background-color: rgba(99, 102, 241, 0.2);
  border-left: 4px solid #6366f1;
}

.tool-item img {
  filter: brightness(1);
}

.tool-item span {
  color: #ffffff;
}

/* 主内容区域样式 */
.main-content {
  flex: 1;
  margin-left: 260px;
  height: 100vh;
  overflow: hidden;
  position: relative;
  width: calc(100% - 260px);
  max-width: calc(100vw - 260px);
}

/* 移动端适配样式 */
@media (max-width: 768px) {
  .container {
    flex-direction: column;
    width: 100%;
  }
  
  .main-content {
    margin-left: 0;
    width: 100%;
    max-width: 100vw;
  }
  
  .sidebar {
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }
  
  .sidebar.expanded {
    transform: translateX(0);
    box-shadow: 2px 0 15px rgba(0, 0, 0, 0.3);
  }
  
  .sidebar-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 999;
  }
  
  .sidebar-overlay.active {
    display: block;
  }
}

/* 自定义滚动条样式 */
.chat-container {
  /* 隐藏滚动条但保留滚动功能 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
  padding-left: 12px !important;
  padding-right: 8px !important;
  position: relative;
  height: calc(100vh - 120px);
  overflow-y: auto;
  overflow-x: hidden;
  width: 100%;
  box-sizing: border-box;
}

/* Webkit浏览器隐藏滚动条 */
.chat-container::-webkit-scrollbar {
  display: none; /* Chrome, Safari, newer versions of Opera */
}

/* 在全局范围内添加滚动条隐藏 */
::-webkit-scrollbar {
  width: 0;
  background: transparent;
}
</style>