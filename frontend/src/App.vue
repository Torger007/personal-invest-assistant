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
      title="AI 投资助手"
      direction="rtl"
      size="480px"
      :before-close="handleDrawerClose"
      class="ai-drawer"
    >
      <template #header>
        <div class="drawer-header">
          <div class="drawer-title">
            <svg class="drawer-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
              <path d="M12 2a10 10 0 0 1 10 10"/>
              <circle cx="12" cy="12" r="4"/>
            </svg>
            <span>AI 投资助手</span>
          </div>
        </div>
      </template>

      <div class="ai-container">
        <el-alert
          title="AI 分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
          type="warning"
          :closable="false"
          class="ai-warning"
        />

        <!-- 对话历史 -->
        <div class="chat-container" ref="chatContainer">
          <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
            <div class="message-avatar">
              <svg v-if="msg.role === 'user'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
              </svg>
            </div>
            <div class="message-content">
              {{ msg.content }}
            </div>
          </div>
          <div v-if="asking" class="message assistant">
            <div class="message-avatar">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
              </svg>
            </div>
            <div class="message-content thinking">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>思考中...</span>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="chat-input-area">
          <el-input
            v-model="question"
            type="textarea"
            :rows="3"
            placeholder="输入你的问题，如：005827 现在能买吗？"
            @keyup.enter.ctrl="sendQuestion"
            :disabled="asking"
            class="chat-input"
          />
          <div class="chat-actions">
            <span class="input-hint">Ctrl + Enter 发送</span>
            <div class="action-buttons">
              <el-button text @click="clearMessages" :disabled="messages.length === 0">
                <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
                清空
              </el-button>
              <el-button
                type="primary"
                :loading="asking"
                @click="sendQuestion"
                class="send-btn"
              >
                <svg v-if="!asking" class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
                </svg>
                发送
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

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
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { agentApi } from './api'

const drawerVisible = ref(false)
const question = ref('')
const asking = ref(false)
const messages = ref([])
const chatContainer = ref(null)
const isDark = ref(document.documentElement.classList.contains('dark'))

const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
}

const sendQuestion = async () => {
  if (!question.value.trim() || asking.value) return

  const userQuestion = question.value.trim()
  messages.value.push({ role: 'user', content: userQuestion })
  question.value = ''
  asking.value = true

  scrollToBottom()

  try {
    const { data } = await agentApi.chat(userQuestion)
    messages.value.push({ role: 'assistant', content: data.answer })
  } catch (e) {
    ElMessage.error('问答失败: ' + (e.response?.data?.detail || e.message))
    messages.value.push({ role: 'assistant', content: '抱歉，问答失败了，请稍后重试。' })
  } finally {
    asking.value = false
    scrollToBottom()
  }
}

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

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.drawer-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-foreground);
}

.drawer-icon {
  width: 22px;
  height: 22px;
  color: var(--color-accent);
}

.ai-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 80px);
}

.ai-warning {
  margin-bottom: 16px;
  border-radius: var(--radius-md);
}

/* === Chat Container === */
.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: var(--color-muted);
  border-radius: var(--radius-lg);
  margin-bottom: 16px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
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
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
}

.message-avatar svg {
  width: 18px;
  height: 18px;
  color: var(--color-foreground-secondary);
}

.message.user .message-avatar {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.message.user .message-avatar svg {
  color: white;
}

.message-content {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  white-space: pre-wrap;
  word-break: break-word;
  line-height: var(--line-height-relaxed);
  font-size: var(--font-size-base);
}

.message.user .message-content {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: white;
  margin-left: auto;
}

.message.assistant .message-content {
  background: var(--color-surface);
  color: var(--color-foreground);
  border: 1px solid var(--color-border);
}

.message-content.thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-foreground-muted);
  font-style: italic;
}

/* === Chat Input === */
.chat-input-area {
  padding: 16px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.chat-input :deep(.el-textarea__inner) {
  background: transparent;
  border: none;
  padding: 0;
  font-family: var(--font-sans);
  resize: none;
}

.chat-input :deep(.el-textarea__inner:focus) {
  box-shadow: none;
}

.chat-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.input-hint {
  font-size: var(--font-size-xs);
  color: var(--color-foreground-muted);
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-icon {
  width: 16px;
  height: 16px;
  margin-right: 4px;
}

.send-btn {
  display: flex;
  align-items: center;
  gap: 6px;
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