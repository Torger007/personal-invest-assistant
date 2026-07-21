<template>
  <el-container>
    <el-header>
      <h1>个人投资助手</h1>
      <el-menu mode="horizontal" :router="true" :ellipsis="false">
        <el-menu-item index="/">市场概览</el-menu-item>
        <el-menu-item index="/funds">基金分析</el-menu-item>
        <el-menu-item index="/sectors">板块走势</el-menu-item>
        <el-menu-item index="/advice">投资建议</el-menu-item>
      </el-menu>
      <el-button type="primary" @click="drawerVisible = true" class="ask-ai-btn">
        问AI
      </el-button>
    </el-header>
    <el-main>
      <router-view />
    </el-main>

    <!-- AI 助手侧边栏 -->
    <el-drawer
      v-model="drawerVisible"
      title="AI 投资助手"
      direction="rtl"
      size="450px"
      :before-close="handleDrawerClose"
    >
      <el-alert
        title="AI 分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
        type="warning"
        :closable="false"
        style="margin-bottom: 16px;"
      />

      <!-- 对话历史 -->
      <div class="chat-container" ref="chatContainer">
        <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
          <div class="message-content">
            {{ msg.content }}
          </div>
        </div>
        <div v-if="asking" class="message assistant">
          <div class="message-content thinking">
            <el-icon class="is-loading"><Loading /></el-icon>
            思考中...
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="chat-input-area">
        <el-input
          v-model="question"
          type="textarea"
          :rows="2"
          placeholder="输入你的问题，如：005827 现在能买吗？"
          @keyup.enter.ctrl="sendQuestion"
          :disabled="asking"
        />
        <el-button
          type="primary"
          :loading="asking"
          @click="sendQuestion"
          style="margin-top: 8px;"
        >
          发送 (Ctrl+Enter)
        </el-button>
      </div>
    </el-drawer>
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

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

const handleDrawerClose = (done) => {
  // 如果正在思考，提示用户
  if (asking.value) {
    ElMessage.warning('AI 正在思考中，请稍候...')
    return
  }
  done()
}
</script>

<style>
#app {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}

.el-header {
  display: flex;
  align-items: center;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.el-header h1 {
  margin: 0 20px 0 0;
  font-size: 20px;
  color: #303133;
}

.ask-ai-btn {
  margin-left: auto;
}
</style>

<style scoped>
.chat-container {
  height: calc(100vh - 280px);
  overflow-y: auto;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.message {
  margin-bottom: 12px;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

.message-content {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  font-size: 14px;
}

.message.user .message-content {
  background: #409eff;
  color: #fff;
}

.message.assistant .message-content {
  background: #fff;
  color: #303133;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.message-content.thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
}

.chat-input-area {
  position: absolute;
  bottom: 20px;
  left: 20px;
  right: 20px;
}
</style>
