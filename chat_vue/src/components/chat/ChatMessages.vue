<template>
  <div class="chat-container">
    <div class="welcome-screen" v-if="messages.length === 0">
      <h2 class="welcome-title">欢迎使用 天汇AI</h2>
      <DotLottieVue
        ref="lottieAnimation"
        style="height: 300px; width: 300px"
        :autoplay="showAnimation"
        :loop="false"
        src="https://lottie.host/075353b3-e4c2-4fa8-91ea-7f32563e1e3b/UQ3swQC3pC.lottie"
        @complete="onAnimationComplete"
      />
    </div>
    
    <div v-else>
      <div 
        v-for="(message, index) in messages" 
        :key="index" 
        :class="['message', message.role === 'user' ? 'user-message' : 'bot-message']"
      >
        <div :class="['avatar', message.role === 'user' ? 'user-avatar' : 'bot-avatar']">
          <template v-if="message.role === 'user'">🧑‍💻</template>
          <template v-else>🤖</template>
        </div>
        <div 
          class="message-content markdown-content" 
          v-if="!message.streaming" 
          v-html="renderedContent(message.content)"
        ></div>
        <div class="message-content" v-else>
          <div v-if="message.content" class="markdown-content" v-html="renderedContent(message.content)"></div>
          <div class="typing-indicator" v-if="message.streaming">
            <div class="wave-dots">
              <div class="dot"></div>
              <div class="dot"></div>
              <div class="dot"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch, nextTick, onBeforeMount } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'
import 'github-markdown-css/github-markdown.css'
import { DotLottieVue } from '@lottiefiles/dotlottie-vue'

// 先定义props
const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  }
})

// 创建代码复制指令
const vCopy = {
  mounted(el, binding) {
    const codeBlock = binding.value;
    const button = el;
    const statusElement = button.nextElementSibling;
    
    button.addEventListener('click', () => {
      navigator.clipboard.writeText(codeBlock.trim())
        .then(() => {
          statusElement.textContent = '已复制';
          setTimeout(() => {
            statusElement.textContent = '复制';
          }, 2000);
        })
        .catch(err => {
          console.error('复制失败:', err);
          statusElement.textContent = '复制失败';
          setTimeout(() => {
            statusElement.textContent = '复制';
          }, 2000);
        });
    });
  }
};

// 在组件挂载前注册指令
onBeforeMount(() => {
  if (typeof window !== 'undefined') {
    // 创建全局函数以供HTML标记中调用
    window.copyCode = (blockId) => {
      const codeBlock = document.getElementById(blockId);
      if (codeBlock) {
        const codeContent = codeBlock.querySelector('code').textContent.trim();
        const button = codeBlock.querySelector('.copy-button');
        const statusElement = button.nextElementSibling;
        
        navigator.clipboard.writeText(codeContent)
          .then(() => {
            statusElement.textContent = '已复制';
            setTimeout(() => {
              statusElement.textContent = '复制';
            }, 2000);
          })
          .catch(err => {
            console.error('复制失败:', err);
            statusElement.textContent = '复制失败';
            setTimeout(() => {
              statusElement.textContent = '复制';
            }, 2000);
          });
      }
    };
  }
});

// Lottie动画相关
const lottieAnimation = ref(null)
const showAnimation = ref(true)

// 监听消息变化，当消息从有到无时重新播放动画
watch(() => props.messages.length, (newLength, oldLength) => {
  if (newLength === 0 && oldLength > 0) {
    resetAnimation()
  }
})

// 监听消息内容变化，但不自动滚动
watch(() => props.messages, () => {
  // 不在这里执行自动滚动，让用户自己控制滚动位置
}, { deep: true })

// 动画完成后的回调函数
const onAnimationComplete = () => {
  // 动画结束后停在最后一帧
  showAnimation.value = false
  if (lottieAnimation.value) {
    // 确保动画停在最后一帧
    lottieAnimation.value.seek('100%')
  }
}

// 重置动画，再次进入欢迎页面时播放
const resetAnimation = () => {
  showAnimation.value = true
  if (lottieAnimation.value) {
    lottieAnimation.value.play()
  }
}

// 组件挂载时
onMounted(() => {
  // 防止动画不触发complete事件
  if (lottieAnimation.value) {
    setTimeout(() => {
      // 如果2秒后还在欢迎页面，检查动画状态
      if (props.messages.length === 0) {
        onAnimationComplete()
      }
    }, 2000)
  }
})

// 创建markdown-it实例并配置
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        // 为Python代码特别处理
        const highlightedCode = hljs.highlight(str, { 
          language: lang, 
          ignoreIllegals: true 
        }).value;
        
        // 返回带有语言类名的代码块
        return `<pre class="hljs"><code class="language-${lang}">${highlightedCode}</code></pre>`;
      } catch (error) {
        console.error('代码高亮出错:', error);
      }
    }
    // 无法识别语言时，返回未格式化的代码并添加浅色样式
    return `<pre class="hljs"><code class="language-plaintext">${md.utils.escapeHtml(str)}</code></pre>`;
  }
})

// 渲染Markdown内容
const renderedContent = (content) => {
  // 如果内容为空或不是字符串，返回空字符串
  if (!content || typeof content !== 'string') return '';
  
  try {
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
      
      // 添加实际回答内容，使用markdown解析
      if (actualResponse) {
        try {
          // 在解析前先保存原始内容，方便修改渲染后的HTML
          let renderedHtml = md.render(actualResponse);
          
          // 为所有代码块添加复制按钮
          renderedHtml = addCopyButtonToCodeBlocks(renderedHtml);
          
          processedContent += `<div class="response-container markdown-body">${renderedHtml}</div>`;
        } catch (error) {
          console.error('Markdown渲染错误:', error);
          processedContent += `<div class="error-content">${actualResponse}</div>`;
        }
      }
      
      return processedContent;
    }
    
    // 如果没有思考过程标记，直接以Markdown解析内容
    let renderedHtml = md.render(content);
    
    // 为所有代码块添加复制按钮
    renderedHtml = addCopyButtonToCodeBlocks(renderedHtml);
    
    return `<div class="markdown-body">${renderedHtml}</div>`;
  } catch (error) {
    console.error('Markdown渲染出错:', error);
    // 出错时以纯文本方式返回内容
    return `<div class="error-content">${content}</div>`;
  }
}

// 为代码块添加复制按钮的辅助函数
const addCopyButtonToCodeBlocks = (html) => {
  // 使用正则表达式匹配所有代码块
  const codeBlockRegex = /<pre class="hljs"><code class="language-([^"]+)">([\s\S]*?)<\/code><\/pre>/g;
  
  // 为每个代码块生成一个唯一ID
  let blockCounter = 0;
  
  // 替换每个代码块，添加复制按钮
  return html.replace(codeBlockRegex, (match, language, codeContent) => {
    const blockId = `code-block-${Date.now()}-${blockCounter++}`;
    const displayLang = language === 'plaintext' ? '' : language;
    
    return `
      <div class="code-block-wrapper" id="${blockId}">
        <div class="code-block-header">
          <button class="copy-button" onclick="copyCode('${blockId}')">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span class="copy-status">复制</span>
          </button>
        </div>
        ${displayLang ? `<div class="code-language-label">${displayLang}</div>` : ''}
        <pre class="hljs"><code class="language-${language}">${codeContent}</code></pre>
      </div>
    `;
  });
}
</script>

<style>
/* 添加一些样式以确保Markdown正确显示 */
.markdown-content {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  line-height: 1.6;
  color: #e0e0ff; /* 确保文字为浅色 */
}

.markdown-content .markdown-body {
  background-color: transparent;
  color: #e0e0ff; /* 明确指定markdown内容为浅色 */
  font-size: 14px;
}

/* Lottie动画样式 */
.welcome-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;
}

.welcome-title {
  margin-bottom: 30px;
  text-align: center;
}

/* 动画容器样式 */
.welcome-screen dotlottie-vue {
  border-radius: 12px;
  box-shadow: 0 5px 20px rgba(99, 102, 241, 0.2);
  margin: 0 auto;
  display: block;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.welcome-screen dotlottie-vue:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 25px rgba(99, 102, 241, 0.3);
}

/* 调整代码块样式 */
.markdown-content pre.hljs {
  margin: 0;
  padding: 0;
  background-color: transparent;
  contain: content; /* 防止内容溢出影响布局 */
}

.markdown-content pre.hljs code {
  display: block;
  padding: 40px 16px 16px;
  color: #e0e0ff;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 14px;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre; /* 保持代码格式 */
  tab-size: 2; /* 设置制表符宽度 */
}

/* 代码行 */
.markdown-content pre.hljs code .line {
  display: block;
  line-height: 1.5;
}

/* 代码行有缩进时的样式 */
.markdown-content pre.hljs code .indent {
  display: inline-block;
  width: 20px;
}

/* 通用的浅色文本样式 */
.markdown-content code {
  color: #e0e0ff;
}

/* 确保代码中的所有元素都是浅色 */
.hljs-keyword, 
.hljs-selector-tag, 
.hljs-subst {
  color: #c678dd !important; /* 紫色 - 关键词 */
}

.hljs-string, 
.hljs-regexp, 
.hljs-addition, 
.hljs-attribute, 
.hljs-meta .hljs-string {
  color: #98c379 !important; /* 绿色 - 字符串 */
}

.hljs-number, 
.hljs-literal {
  color: #d19a66 !important; /* 橙色 - 数字 */
}

.hljs-doctag,
.hljs-tag, 
.hljs-name, 
.hljs-selector-id,
.hljs-selector-class, 
.hljs-meta, 
.hljs-built_in {
  color: #61afef !important; /* 蓝色 - 标签、函数 */
}

.hljs-title, 
.hljs-section, 
.hljs-selector-id {
  color: #61afef !important; /* 蓝色 - 函数名、类名 */
}

.hljs-comment, 
.hljs-quote {
  color: #a0a8b7 !important; /* 灰色 - 注释 */
}

.hljs-variable, 
.hljs-template-variable, 
.hljs-type, 
.hljs-params {
  color: #e6c07b !important; /* 黄色 - 变量 */
}

/* 代码行号 */
.hljs-ln-numbers {
  color: #7f848e !important;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  -khtml-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

/* 内联代码样式 */
.markdown-content code:not(.hljs) {
  background-color: rgba(99, 102, 241, 0.1);
  border-radius: 3px;
  font-size: 85%;
  padding: 0.2em 0.4em;
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
  color: #e0e0ff; /* 确保内联代码文本为浅色 */
}

/* 特定编程语言样式 */
.language-c, .language-cpp {
  color: #f1c40f; /* 黄色调 */
}

.language-cs, .language-java {
  color: #e74c3c; /* 红色调 */
}

.language-python {
  color: #2ecc71; /* 绿色调 */
}

.language-javascript, .language-typescript {
  color: #3498db; /* 蓝色调 */
}

.language-html, .language-css, .language-json {
  color: #9b59b6; /* 紫色调 */
}

/* 调整表格样式 */
.markdown-content table {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
}

.markdown-content table th,
.markdown-content table td {
  border: 1px solid rgba(99, 102, 241, 0.2);
  padding: 6px 13px;
}

.markdown-content table tr:nth-child(2n) {
  background-color: rgba(99, 102, 241, 0.05);
}

/* 错误内容样式 */
.error-content {
  background-color: rgba(239, 68, 68, 0.05);
  padding: 10px;
  border-left: 3px solid #ef4444;
  white-space: pre-wrap;
  font-family: monospace;
  color: #ffcccc; /* 使用浅红色以提高错误消息在深色背景下的可读性 */
  margin: 8px 0;
  border-radius: 0 4px 4px 0;
}

/* 思考过程样式优化 */
.thinking-content {
  margin: 10px 0;
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 6px;
  overflow: hidden;
  background-color: rgba(30, 33, 48, 0.6);
}

.thinking-content summary {
  padding: 8px 12px;
  background-color: rgba(99, 102, 241, 0.1);
  color: #e0e0ff; /* 确保标题文字为浅色 */
  cursor: pointer;
  user-select: none;
  font-weight: 500;
  display: flex;
  align-items: center;
}

.thinking-content summary::before {
  content: '▶';
  margin-right: 8px;
  font-size: 12px;
  color: #a5b4fc; /* 箭头颜色设置为浅紫色 */
  transition: transform 0.2s;
}

.thinking-content details[open] summary::before {
  transform: rotate(90deg);
}

.thinking-content pre {
  margin: 0;
  padding: 12px;
  overflow: auto;
  background-color: rgba(0, 0, 0, 0.1);
  color: #e0e0ff; /* 确保代码内容为浅色 */
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 14px;
}

.thinking-content summary:hover {
  background-color: rgba(99, 102, 241, 0.2);
  color: #a5b4fc; /* 悬停时变为淡紫色 */
}

/* Python代码特定高亮 */
.language-python .hljs-keyword {
  color: #ff79c6 !important; /* 亮粉色 - Python关键字 (while, if, for等) */
}

.language-python .hljs-built_in {
  color: #8be9fd !important; /* 青色 - Python内置函数 (print, len等) */
}

.language-python .hljs-number {
  color: #bd93f9 !important; /* 紫色 - 数字 */
}

.language-python .hljs-string {
  color: #f1fa8c !important; /* 黄色 - 字符串 */
}

.language-python .hljs-comment {
  color: #6272a4 !important; /* 浅灰蓝色 - 注释 */
}

.language-python .hljs-operator {
  color: #ff79c6 !important; /* 亮粉色 - 运算符 */
}

.language-python .hljs-variable,
.language-python .hljs-params {
  color: #50fa7b !important; /* 绿色 - 变量和参数 */
}

/* 处理缩进和代码块边距 */
.markdown-content pre {
  margin: 1em 0;
  padding: 0;
  background-color: transparent;
}

.markdown-content pre code {
  display: block;
  overflow-x: auto;
  padding: 16px;
  border-radius: 6px;
  line-height: 1.5;
}

/* 代码块内部样式 - 覆盖highlight.js默认样式 */
.hljs,
.hljs *,
.hljs-emphasis,
.hljs-strong,
.hljs-keyword,
.hljs-selector-tag,
.hljs-doctag,
.hljs-section,
.hljs-name,
.hljs-tag,
.hljs-subst,
.hljs-number,
.hljs-symbol,
.hljs-class,
.hljs-title,
.hljs-function,
.hljs-string {
  color: #e0e0ff !important; /* 默认所有代码元素为浅色 */
  font-weight: normal !important;
  background: transparent !important;
}

/* 确保默认所有代码颜色为浅色 */
.language-plaintext {
  color: #e0e0ff !important;
}

/* 针对您图片中所示的Python代码特别处理 */
/* 变量名的样式 */
.language-python .hljs-name {
  color: #50fa7b !important; /* 绿色 - 变量名 */
}

/* 运算符、等号的样式 */
.language-python .hljs-operator,
.language-python .hljs-punctuation {
  color: #ff79c6 !important; /* 粉色 - 运算符和标点 */
}

/* 数字的样式 */
.language-python .hljs-number {
  color: #bd93f9 !important; /* 紫色 - 数字 */
}

/* print函数的样式 */
.language-python .hljs-built_in,
.language-python .hljs-title.function_ {
  color: #8be9fd !important; /* 青色 - 内置函数 */
}

/* while等关键字的样式 */
.language-python .hljs-keyword,
.language-python .hljs-title.class_ {
  color: #ff79c6 !important; /* 粉色 - 关键字 */
}

/* 代码块包装容器 */
.code-block-wrapper {
  position: relative;
  margin: 1em 0;
  border-radius: 8px;
  overflow: hidden;
  background-color: #1e2133;
  border: 1px solid rgba(99, 102, 241, 0.2);
  contain: content; /* 防止内容溢出影响布局 */
}

/* 代码块头部样式 */
.code-block-header {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 10;
  padding: 4px;
  border-radius: 4px;
  background: rgba(40, 44, 61, 0.8);
  backdrop-filter: blur(4px);
  opacity: 0;
  transition: opacity 0.2s ease-in-out;
}

/* 在桌面端，只在悬停时显示复制按钮 */
@media (min-width: 768px) {
  .code-block-wrapper:hover .code-block-header {
    opacity: 1;
  }
}

/* 在移动端，始终显示复制按钮 */
@media (max-width: 767px) {
  .code-block-header {
    opacity: 1;
  }
}

.copy-button {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: transparent;
  border: none;
  color: #a0a8b7;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s ease;
}

.copy-button:hover {
  color: #e0e0ff;
  background-color: rgba(99, 102, 241, 0.3);
}

.copy-button svg {
  width: 14px;
  height: 14px;
}

.copy-status {
  font-size: 12px;
}

.code-language-label {
  position: absolute;
  top: 8px;
  left: 12px;
  font-size: 12px;
  color: #a0a8b7;
  font-family: 'JetBrains Mono', monospace;
}

/* 消息样式 */
.message {
  display: flex;
  margin-bottom: 20px;
  max-width: 100%;
  word-wrap: break-word;
  align-items: flex-start;
}

.message-content {
  line-height: 1.6;
  background-color: rgba(30, 33, 48, 0.8);
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  position: relative;
  max-width: 65%;
  width: auto;
  overflow-wrap: break-word;
  color: #e0e0ff;
  contain: content; /* 防止内容溢出影响布局 */
}

.user-message {
  flex-direction: row-reverse;
  justify-content: flex-start;
}

.user-message .message-content {
  background-color: rgba(99, 102, 241, 0.2);
  border: 1px solid rgba(99, 102, 241, 0.3);
  margin-right: 16px;
  margin-left: 0;
  color: #e0e0ff;
}

.bot-message {
  justify-content: flex-start;
}

.bot-message .message-content {
  background-color: rgba(30, 33, 48, 0.8);
  border: 1px solid rgba(30, 33, 48, 0.8);
  margin-left: 16px;
  max-width: 85%;
  color: #e0e0ff;
}

/* 桌面端固定宽度 */
@media (min-width: 768px) {
  .bot-message .message-content {
    width: 800px;
    max-width: 800px;
  }
  
  .user-message .message-content {
    width: auto;
    max-width: 600px;
  }
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

/* 聊天容器样式 */
.chat-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  scrollbar-width: thin;
  scrollbar-color: rgba(99, 102, 241, 0.5) #1e2130;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  scroll-behavior: smooth; /* 平滑滚动 */
}
</style> 