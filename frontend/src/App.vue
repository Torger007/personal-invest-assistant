<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-brand">
        <svg class="brand-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M3 13.5L9 19.5L21 7.5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M14 7.5H21V14.5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <h1 class="brand-title">投资助手</h1>
      </div>

      <el-menu mode="horizontal" :router="true" :ellipsis="false" class="nav-menu">
        <el-menu-item index="/">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7" rx="1"/>
            <rect x="14" y="3" width="7" height="7" rx="1"/>
            <rect x="3" y="14" width="7" height="7" rx="1"/>
            <rect x="14" y="14" width="7" height="7" rx="1"/>
          </svg>
          <span>市场概览</span>
        </el-menu-item>
        <el-menu-item index="/funds">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7L12 12L22 7L12 2Z"/>
            <path d="M2 17L12 22L22 17"/>
            <path d="M2 12L12 17L22 12"/>
          </svg>
          <span>基金分析</span>
        </el-menu-item>
        <el-menu-item index="/sectors">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 20V10"/>
            <path d="M12 20V4"/>
            <path d="M6 20V14"/>
          </svg>
          <span>板块走势</span>
        </el-menu-item>
        <el-menu-item index="/advice">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 12.728l-.707.707M12 21v-1m4.95-2.05l.707.707M4.95 4.95l.707.707"/>
            <circle cx="12" cy="12" r="4"/>
          </svg>
          <span>投资建议</span>
        </el-menu-item>
      </el-menu>

      <div class="header-actions">
        <el-tooltip content="切换主题" placement="bottom">
          <el-button class="theme-toggle" @click="toggleTheme" circle>
            <svg v-if="isDark" class="theme-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="5"/>
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
            </svg>
            <svg v-else class="theme-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </el-button>
        </el-tooltip>

        <el-button type="primary" @click="drawerVisible = true" class="ask-ai-btn">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          <span>问 AI</span>
        </el-button>
      </div>
    </el-header>

    <el-main class="app-main">
      <router-view @open-ai-drawer="drawerVisible = true" />
    </el-main>

    <!-- AI 助手侧边栏 -->
    <el-drawer
      v-model="drawerVisible"
      direction="rtl"
      size="480px"
      :before-close="handleDrawerClose"
      class="ai-drawer"
      :with-header="false"
    >
      <!-- 自定义 Header -->
      <div class="ai-header">
        <div class="ai-header-bg"></div>
        <div class="ai-header-content">
          <div class="ai-header-left">
            <div class="ai-logo">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
                <path d="M12 2a10 10 0 0 1 10 10"/>
                <circle cx="12" cy="12" r="4"/>
              </svg>
            </div>
            <div class="ai-header-title">
              <h3>AI 投资助手</h3>
            </div>
          </div>
          <button class="ai-close-btn" @click="drawerVisible = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
      </div>

      <div class="ai-container">
        <section class="conversation-history">
          <div class="history-toolbar">
            <button
              class="history-toggle"
              type="button"
              :aria-expanded="historyExpanded"
              @click="historyExpanded = !historyExpanded"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="9"/>
                <path d="M12 7v5l3 2"/>
              </svg>
              <span>历史会话</span>
              <span v-if="conversations.length" class="history-count">{{ conversations.length }}</span>
              <span class="history-chevron">{{ historyExpanded ? '▲' : '▼' }}</span>
            </button>
            <el-tooltip content="新建会话" placement="bottom">
              <button class="history-icon-button" type="button" :disabled="asking" @click="startNewConversation">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
              </button>
            </el-tooltip>
          </div>
          <div v-if="historyExpanded" class="history-list" v-loading="historyLoading">
            <div v-if="!historyLoading && !conversations.length" class="history-empty">暂无历史会话</div>
            <div v-for="conversation in conversations" :key="conversation.id" class="history-row" :class="{ active: conversation.id === currentConversationId }">
              <button type="button" class="history-row-main" :disabled="asking" @click="restoreConversation(conversation.id)">
                <span class="history-date">{{ formatConversationTime(conversation.last_message_at) }}</span>
                <span class="history-title">{{ conversation.title }}</span>
              </button>
              <el-tooltip content="归档会话" placement="left">
                <button class="history-icon-button archive" type="button" :disabled="asking" @click="archiveConversation(conversation.id)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16v13H4zM3 4h18v3H3zM9 11h6"/></svg>
                </button>
              </el-tooltip>
            </div>
          </div>
        </section>

        <!-- 对话历史 -->
        <div class="chat-container" ref="chatContainer">
          <!-- 欢迎引导（无消息时显示） -->
          <div v-if="messages.length === 0 && !asking" class="welcome-section">
            <div class="welcome-card">
              <div class="welcome-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
                  <path d="M12 2a10 10 0 0 1 10 10"/>
                  <circle cx="12" cy="12" r="4"/>
                </svg>
              </div>
              <h4 class="welcome-title">你好，我是个人投资助手</h4>
              <p class="welcome-desc">我可以帮你分析基金、解读市场、提供投资建议</p>
            </div>
            <div class="quick-questions">
              <p class="quick-label">试试这些：</p>
              <div class="quick-btns">
                <button class="quick-btn" @click="askQuick('005827 现在能买吗？')">
                  <span class="quick-icon">📈</span>
                  <span>005827 现在能买吗？</span>
                </button>
                <button class="quick-btn" @click="askQuick('帮我分析当前持仓')">
                  <span class="quick-icon">💼</span>
                  <span>帮我分析当前持仓</span>
                </button>
                <button class="quick-btn" @click="askQuick('今天大盘走势如何？')">
                  <span class="quick-icon">📊</span>
                  <span>今天大盘走势如何？</span>
                </button>
              </div>
            </div>
          </div>

          <!-- 消息列表 -->
          <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
            <div class="message-avatar">
              <svg v-if="msg.role === 'user'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
                <circle cx="12" cy="12" r="4"/>
              </svg>
            </div>
            <div class="message-body">
              <div v-if="msg.progress?.length" class="tool-progress">
                <div v-for="(step, stepIndex) in msg.progress" :key="`${step.name}-${stepIndex}`" :class="['tool-step', step.status]">
                  <span class="step-indicator">
                    <span v-if="step.status === 'running'" class="step-spinner"></span>
                    <svg v-else-if="step.status === 'success'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                      <path d="M20 6L9 17l-5-5"/>
                    </svg>
                    <svg v-else-if="step.status === 'error'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                      <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                  </span>
                  <span class="step-text">{{ toolLabel(step) }}</span>
                </div>
              </div>
              <div v-if="msg.content" class="message-content">{{ msg.content }}</div>
              <button v-if="msg.analysisId" type="button" class="report-link" @click="viewReport(msg.analysisId)">查看报告</button>
            </div>
          </div>

          <!-- 思考中状态 -->
          <div v-if="asking && messages.length > 0 && !messages[messages.length - 1]?.progress?.length" class="message assistant">
            <div class="message-avatar">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
                <circle cx="12" cy="12" r="4"/>
              </svg>
            </div>
            <div class="message-body">
              <div class="thinking-indicator">
                <span class="thinking-dot"></span>
                <span class="thinking-dot"></span>
                <span class="thinking-dot"></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部输入区域 -->
        <div class="chat-footer">
          <div class="input-wrapper" :class="{ focused: inputFocused }">
            <el-input
              v-model="question"
              type="textarea"
              :rows="2"
              placeholder="输入你的问题..."
              @keyup.enter.ctrl="sendQuestion"
              @focus="inputFocused = true"
              @blur="inputFocused = false"
              :disabled="asking"
              class="chat-input"
              resize="none"
            />
          </div>
          <div class="footer-actions">
            <div class="input-hint">
              <kbd>Ctrl</kbd> + <kbd>Enter</kbd> 发送
            </div>
            <div class="action-btns">
              <el-button text size="small" @click="startNewConversation" :disabled="asking" class="clear-btn">
                <svg class="btn-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 5v14M5 12h14"/>
                </svg>
                新对话
              </el-button>
              <el-button
                type="primary"
                :loading="asking"
                @click="sendQuestion"
                class="send-btn"
                :disabled="!question.trim() && !asking"
              >
                <span v-if="!asking">发送</span>
                <span v-else>思考中...</span>
                <svg v-if="!asking" class="btn-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
                </svg>
              </el-button>
            </div>
          </div>
          <div class="footer-disclaimer">
            <svg class="disclaimer-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 9v4M12 17h.01"/>
            </svg>
            <span>AI 分析仅供参考，投资有风险，入市需谨慎</span>
          </div>
        </div>
      </div>
    </el-drawer>

    <el-dialog v-model="reportVisible" title="分析报告" width="560px" append-to-body>
      <div v-loading="reportLoading" class="report-dialog-content">
        <template v-if="currentReport">
          <p class="report-meta">耗时 {{ currentReport.duration }} 秒 · {{ currentReport.created_at }}</p>
          <div class="report-summary">{{ currentReport.summary }}</div>
          <div v-if="currentReport.trace?.tools?.length" class="report-tools">
            <span v-for="tool in currentReport.trace.tools" :key="`${tool.name}-${tool.started_at || ''}`">{{ tool.name }}</span>
          </div>
        </template>
      </div>
    </el-dialog>

    <!-- 悬浮 AI 助手球 -->
    <div class="ai-fab" @click="drawerVisible = true" v-if="!drawerVisible">
      <div class="ai-fab-inner">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
          <path d="M12 2a10 10 0 0 1 10 10"/>
          <circle cx="12" cy="12" r="4"/>
        </svg>
      </div>
      <div class="ai-fab-pulse"></div>
    </div>
  </el-container>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { agentApi } from './api'

const drawerVisible = ref(false)
const question = ref('')
const asking = ref(false)
const messages = ref([])
const chatContainer = ref(null)
const isDark = ref(document.documentElement.classList.contains('dark'))
const inputFocused = ref(false)
const conversations = ref([])
const currentConversationId = ref(null)
const historyExpanded = ref(false)
const historyLoading = ref(false)
const reportVisible = ref(false)
const reportLoading = ref(false)
const currentReport = ref(null)

const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
}

const askQuick = (text) => {
  question.value = text
  sendQuestion()
}

const sendQuestion = async () => {
  if (!question.value.trim() || asking.value) return

  const userQuestion = question.value.trim()
  messages.value.push({ role: 'user', content: userQuestion })
  messages.value.push({ role: 'assistant', content: '', progress: [] })
  // Mutate Vue's reactive proxy, not the original plain object, so each SSE
  // event immediately updates the drawer instead of appearing at completion.
  const assistantMessage = messages.value[messages.value.length - 1]
  question.value = ''
  asking.value = true

  scrollToBottom()

  try {
    await agentApi.chatStream(userQuestion, currentConversationId.value, event => {
      if (event.type === 'conversation') {
        currentConversationId.value = event.conversation_id
      } else if (event.type === 'tool_started') {
        assistantMessage.progress.push({ name: event.name, status: 'running' })
      } else if (event.type === 'tool_completed') {
        const step = [...assistantMessage.progress].reverse().find(item => item.name === event.name && item.status === 'running')
        if (step) step.status = event.status
      } else if (event.type === 'summarizing') {
        assistantMessage.progress.push({ name: 'summarizing', status: 'running' })
      } else if (event.type === 'waiting' && event.stage === 'summarizing') {
        const step = assistantMessage.progress.find(item => item.name === 'summarizing' && item.status === 'running')
        if (step) step.elapsed = event.elapsed_ms
      } else if (event.type === 'token') {
        assistantMessage.content += event.content
      } else if (event.type === 'complete') {
        assistantMessage.content = event.answer || assistantMessage.content
        assistantMessage.analysisId = event.analysis_id || null
        assistantMessage.messageId = event.message_id || null
        const step = assistantMessage.progress.find(item => item.name === 'summarizing' && item.status === 'running')
        if (step) step.status = 'success'
      } else if (event.type === 'error') {
        assistantMessage.content = `抱歉，问答失败了：${event.message}`
      }
      scrollToBottom()
    })
  } catch (e) {
    ElMessage.error('问答失败: ' + e.message)
    assistantMessage.content = '抱歉，问答失败了，请稍后重试。'
  } finally {
    asking.value = false
    loadConversations()
    scrollToBottom()
  }
}

const toolLabel = (step) => {
  if (step.name === 'summarizing') {
    return `正在生成结论${step.elapsed ? `，已等待 ${Math.ceil(step.elapsed / 1000)} 秒` : ''}`
  }
  return ({
  get_portfolio: '正在读取当前持仓',
  get_market_overview: '正在读取市场概览',
  get_sector_trend: '正在分析板块趋势',
  get_latest_advice: '正在读取系统建议',
  generate_advice: '正在生成系统建议',
  compare_funds: '正在比较基金',
  get_fund_info: '正在读取基金信息',
  get_fund_nav: '正在获取基金净值',
  analyze_technical: '正在分析技术面',
  get_fund_flow: '正在读取资金流',
  get_analysis_history: '正在读取历史判断',
  summarizing: '正在生成结论'
}[step.name] || step.name)
}

const loadConversations = async () => {
  historyLoading.value = true
  try {
    const { data } = await agentApi.getConversations()
    conversations.value = data.conversations || []
  } catch (error) {
    ElMessage.error('加载历史会话失败: ' + error.message)
  } finally {
    historyLoading.value = false
  }
}

const startNewConversation = async () => {
  if (asking.value) return
  try {
    const { data } = await agentApi.createConversation()
    currentConversationId.value = data.id
    messages.value = []
    question.value = ''
    await loadConversations()
    ElMessage.success('已新建对话')
  } catch (error) {
    ElMessage.error('新建对话失败: ' + error.message)
  }
}

const restoreConversation = async (conversationId) => {
  if (asking.value || conversationId === currentConversationId.value) {
    historyExpanded.value = false
    return
  }
  try {
    const { data } = await agentApi.getConversation(conversationId)
    currentConversationId.value = data.id
    messages.value = (data.messages || []).map(message => ({
      role: message.role,
      content: message.content,
      analysisId: message.analysis_id,
      messageId: message.id,
      progress: []
    }))
    historyExpanded.value = false
    scrollToBottom()
  } catch (error) {
    ElMessage.error('恢复历史会话失败: ' + error.message)
  }
}

const archiveConversation = async (conversationId) => {
  if (asking.value) return
  try {
    await agentApi.archiveConversation(conversationId)
    if (conversationId === currentConversationId.value) {
      currentConversationId.value = null
      messages.value = []
    }
    await loadConversations()
  } catch (error) {
    ElMessage.error('归档会话失败: ' + error.message)
  }
}

const viewReport = async (analysisId) => {
  reportVisible.value = true
  reportLoading.value = true
  currentReport.value = null
  try {
    const { data } = await agentApi.getReport(analysisId)
    currentReport.value = data
  } catch (error) {
    ElMessage.error('加载报告失败: ' + error.message)
  } finally {
    reportLoading.value = false
  }
}

const formatConversationTime = (value) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  if (isToday) return `今天 ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (date.toDateString() === yesterday.toDateString()) return `昨天 ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

onMounted(loadConversations)

const clearMessages = () => {
  messages.value = []
  ElMessage.success('对话已清空')
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

const handleDrawerClose = (done) => {
  if (asking.value) {
    ElMessage.warning('AI 正在思考中，请稍候...')
    return
  }
  done()
}
</script>

<style>
/* Global App Styles */
#app {
  font-family: var(--font-sans);
  min-height: 100vh;
  background-color: var(--color-background);
}
</style>

<style scoped>
.app-container {
  min-height: 100vh;
}

/* === Header === */
.app-header {
  display: flex;
  align-items: center;
  height: 64px;
  padding: 0 24px;
  background-color: var(--color-surface);
  border-bottom: 1px solid var(--color-border-light);
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  backdrop-filter: blur(8px);
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.brand-icon {
  width: 28px;
  height: 28px;
  color: var(--color-primary);
}

.brand-title {
  margin: 0;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-foreground);
  letter-spacing: -0.02em;
}

.nav-menu {
  flex: 1;
  display: flex;
  justify-content: center;
}

.nav-icon {
  width: 16px;
  height: 16px;
  margin-right: 6px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.theme-toggle {
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-foreground-secondary);
  transition: all var(--transition-fast);
}

.theme-toggle:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(30, 64, 175, 0.04);
}

.theme-icon {
  width: 18px;
  height: 18px;
}

.ask-ai-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, var(--color-accent) 0%, #F59E0B 100%);
  border: none;
  border-radius: var(--radius-full);
  font-weight: var(--font-weight-semibold);
  box-shadow: 0 4px 12px rgba(217, 119, 6, 0.25);
  transition: all var(--transition-normal);
}

.ask-ai-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(217, 119, 6, 0.35);
}

.btn-icon {
  width: 18px;
  height: 18px;
}

/* === Main Content === */
.app-main {
  padding: 0;
  background-color: var(--color-background);
}

/* === AI Drawer === */
.ai-drawer {
  --el-drawer-bg-color: var(--color-surface);
}

.ai-drawer :deep(.el-drawer__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* === AI Header === */
.ai-header {
  position: relative;
  padding: 20px 24px;
  overflow: hidden;
}

.ai-header-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(30, 64, 175, 0.08) 0%, rgba(217, 119, 6, 0.12) 100%);
}

.ai-header-content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ai-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.ai-logo {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-accent) 0%, #F59E0B 100%);
  border-radius: 14px;
  box-shadow: 0 4px 12px rgba(217, 119, 6, 0.25);
}

.ai-logo svg {
  width: 24px;
  height: 24px;
  color: white;
}

.ai-header-title h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-foreground);
}

.ai-close-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-muted);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.ai-close-btn:hover {
  background: var(--color-border);
}

.ai-close-btn svg {
  width: 18px;
  height: 18px;
  color: var(--color-foreground-secondary);
}

/* === AI Container === */
.ai-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.conversation-history {
  flex: 0 0 auto;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.history-toolbar {
  min-height: 44px;
  padding: 0 16px 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-toggle,
.history-icon-button,
.history-row-main {
  border: 0;
  background: transparent;
  color: var(--color-foreground-secondary);
  cursor: pointer;
}

.history-toggle {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.history-toggle svg,
.history-icon-button svg {
  width: 16px;
  height: 16px;
}

.history-count {
  min-width: 18px;
  padding: 1px 5px;
  border-radius: 9px;
  background: var(--color-muted);
  font-size: 11px;
  text-align: center;
}

.history-chevron {
  font-size: 9px;
  margin-left: 2px;
}

.history-icon-button {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.history-icon-button:hover:not(:disabled),
.history-toggle:hover {
  color: var(--color-accent);
  background: var(--color-muted);
}

.history-icon-button:disabled,
.history-row-main:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.history-list {
  max-height: 220px;
  overflow-y: auto;
  border-top: 1px solid var(--color-border);
}

.history-empty {
  padding: 16px 20px;
  font-size: 13px;
  color: var(--color-foreground-muted);
}

.history-row {
  min-height: 52px;
  display: flex;
  align-items: center;
  padding: 0 12px 0 20px;
  border-bottom: 1px solid var(--color-border);
}

.history-row:last-child {
  border-bottom: 0;
}

.history-row.active {
  background: var(--color-muted);
}

.history-row-main {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 2px;
  padding: 8px 0;
  text-align: left;
}

.history-row-main:hover:not(:disabled) .history-title {
  color: var(--color-accent);
}

.history-date {
  font-size: 11px;
  color: var(--color-foreground-muted);
}

.history-title {
  overflow: hidden;
  color: var(--color-foreground);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-icon-button.archive {
  opacity: 0;
}

.history-row:hover .history-icon-button.archive,
.history-row.active .history-icon-button.archive {
  opacity: 1;
}

/* === Chat Container === */
.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: var(--color-background);
}

/* === Welcome Section === */
.welcome-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 0;
}

.welcome-card {
  text-align: center;
  padding: 32px 24px;
  background: var(--color-surface);
  border-radius: 20px;
  border: 1px solid var(--color-border);
  margin-bottom: 24px;
  max-width: 320px;
}

.welcome-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(30, 64, 175, 0.1) 0%, rgba(217, 119, 6, 0.15) 100%);
  border-radius: 20px;
}

.welcome-icon svg {
  width: 32px;
  height: 32px;
  color: var(--color-accent);
}

.welcome-title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-foreground);
}

.welcome-desc {
  margin: 0;
  font-size: 14px;
  color: var(--color-foreground-secondary);
  line-height: 1.5;
}

.quick-questions {
  width: 100%;
  max-width: 360px;
}

.quick-label {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--color-foreground-muted);
}

.quick-btns {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.quick-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.quick-btn:hover {
  border-color: var(--color-accent);
  box-shadow: 0 2px 12px rgba(217, 119, 6, 0.15);
  transform: translateX(4px);
}

.quick-icon {
  font-size: 18px;
}

.quick-btn span:last-child {
  font-size: 14px;
  color: var(--color-foreground);
}

/* === Messages === */
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  animation: messageIn 0.3s ease;
}

@keyframes messageIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  border-radius: 12px;
  border: 1px solid var(--color-border);
}

.message-avatar svg {
  width: 18px;
  height: 18px;
  color: var(--color-foreground-secondary);
}

.message.user .message-avatar {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  border-color: transparent;
}

.message.user .message-avatar svg {
  color: white;
}

.message-body {
  max-width: 80%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message-content {
  padding: 14px 18px;
  border-radius: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  font-size: 14px;
}

.message.user .message-content {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: white;
  border-radius: 16px 16px 4px 16px;
}

.message.assistant .message-body {
  align-items: flex-start;
}

.message.assistant .message-content {
  background: var(--color-surface);
  color: var(--color-foreground);
  border: 1px solid var(--color-border);
  border-radius: 16px 16px 16px 4px;
  border-left: 3px solid var(--color-accent);
}

.report-link {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--color-accent);
  cursor: pointer;
  font-size: 13px;
}

.report-link:hover {
  text-decoration: underline;
}

.report-dialog-content {
  min-height: 72px;
}

.report-meta {
  margin: 0 0 12px;
  color: var(--color-foreground-muted);
  font-size: 12px;
}

.report-summary {
  white-space: pre-wrap;
  color: var(--color-foreground);
  line-height: 1.65;
}

.report-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 16px;
}

.report-tools span {
  padding: 3px 7px;
  border-radius: 4px;
  background: var(--color-muted);
  color: var(--color-foreground-secondary);
  font-size: 12px;
}

/* === Tool Progress === */
.tool-progress {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px;
  background: var(--color-muted);
  border-radius: 12px;
  border: 1px solid var(--color-border);
}

.tool-step {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--color-foreground-secondary);
}

.step-indicator {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  border-radius: 50%;
  border: 1px solid var(--color-border);
}

.step-indicator svg {
  width: 12px;
  height: 12px;
}

.tool-step.success .step-indicator {
  background: rgba(22, 163, 74, 0.1);
  border-color: #16A34A;
}

.tool-step.success .step-indicator svg {
  color: #16A34A;
}

.tool-step.error .step-indicator {
  background: rgba(220, 38, 38, 0.1);
  border-color: #DC2626;
}

.tool-step.error .step-indicator svg {
  color: #DC2626;
}

.step-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid var(--color-primary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.tool-step.running .step-indicator {
  border-color: var(--color-primary);
}

/* === Thinking Indicator === */
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 14px 18px;
  background: var(--color-surface);
  border-radius: 16px;
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-accent);
}

.thinking-dot {
  width: 8px;
  height: 8px;
  background: var(--color-accent);
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite;
}

.thinking-dot:nth-child(1) { animation-delay: 0s; }
.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

/* === Chat Footer === */
.chat-footer {
  padding: 16px 20px;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
}

.input-wrapper {
  position: relative;
  border-radius: 16px;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  transition: all 0.2s ease;
}

.input-wrapper.focused {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.1);
}

.chat-input :deep(.el-textarea__inner) {
  background: transparent;
  border: none;
  padding: 14px 16px;
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  resize: none;
}

.chat-input :deep(.el-textarea__inner:focus) {
  box-shadow: none;
}

.chat-input :deep(.el-textarea__inner::placeholder) {
  color: var(--color-foreground-muted);
}

.footer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}

.input-hint {
  font-size: 12px;
  color: var(--color-foreground-muted);
}

.input-hint kbd {
  padding: 2px 6px;
  background: var(--color-muted);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 11px;
  font-family: inherit;
}

.action-btns {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-icon-sm {
  width: 14px;
  height: 14px;
  margin-right: 4px;
}

.clear-btn {
  color: var(--color-foreground-muted);
}

.clear-btn:hover {
  color: var(--color-foreground-secondary);
}

.send-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: linear-gradient(135deg, var(--color-accent) 0%, #F59E0B 100%);
  border: none;
  border-radius: 12px;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(217, 119, 6, 0.25);
  transition: all 0.2s ease;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(217, 119, 6, 0.35);
}

.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.send-btn .btn-icon-sm {
  margin-right: 0;
  margin-left: 4px;
}

.footer-disclaimer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
  font-size: 12px;
  color: var(--color-foreground-muted);
}

.disclaimer-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

/* === AI Floating Action Button === */
.ai-fab {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 56px;
  height: 56px;
  cursor: pointer;
  z-index: var(--z-modal);
}

.ai-fab-inner {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-accent) 0%, #F59E0B 100%);
  border-radius: 50%;
  box-shadow: 0 4px 16px rgba(217, 119, 6, 0.4);
  transition: all 0.3s ease;
}

.ai-fab:hover .ai-fab-inner {
  transform: scale(1.1);
  box-shadow: 0 6px 24px rgba(217, 119, 6, 0.5);
}

.ai-fab-inner svg {
  width: 28px;
  height: 28px;
  color: white;
}

.ai-fab-pulse {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid var(--color-accent);
  opacity: 0;
  animation: pulse-ring 2s ease-out infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(1); opacity: 0.6; }
  100% { transform: scale(1.3); opacity: 0; }
}

/* === Responsive === */
@media (max-width: 768px) {
  .app-header {
    padding: 0 16px;
  }

  .brand-title {
    display: none;
  }

  .nav-menu {
    margin: 0 8px;
  }

  .nav-menu .el-menu-item {
    padding: 0 12px;
  }

  .nav-menu .el-menu-item span {
    display: none;
  }

  .nav-icon {
    margin-right: 0;
  }

  .ask-ai-btn span {
    display: none;
  }

  .ask-ai-btn {
    padding: 10px;
    border-radius: var(--radius-full);
  }
}
</style>
