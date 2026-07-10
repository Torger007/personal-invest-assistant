<template>
  <div class="agent-page">
    <h2>AI 投资助手</h2>
    <el-alert
      title="AI 分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
      type="warning"
      :closable="false"
      style="margin-bottom: 16px;"
    />

    <!-- 问答交互 -->
    <el-card>
      <template #header>
        <span>投资问答</span>
      </template>
      <div class="chat-input">
        <el-input
          v-model="question"
          type="textarea"
          :rows="2"
          placeholder="输入你的问题，如：005827 现在能买吗？"
          @keyup.enter.ctrl="sendQuestion"
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
      <div v-if="answer" class="chat-answer">
        <el-divider />
        <pre class="answer-text">{{ answer }}</pre>
      </div>
    </el-card>

    <!-- 自主分析 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>自主分析</span>
          <el-switch
            v-model="autoEnabled"
            active-text="开启"
            inactive-text="关闭"
            @change="toggleAutoMode"
          />
        </div>
      </template>
      <p>开启后，每个交易日收盘后自动分析你的持仓基金。</p>
      <el-button
        type="primary"
        :loading="analyzing"
        @click="triggerAnalysis"
      >
        {{ analyzing ? '分析中...' : '立即分析' }}
      </el-button>
      <div v-if="lastResult" class="analysis-result">
        <el-divider />
        <pre class="answer-text">{{ lastResult }}</pre>
      </div>
    </el-card>

    <!-- 分析历史 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>分析历史</span>
      </template>
      <el-table :data="history" stripe v-loading="loadingHistory">
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.type === 'autonomous' ? 'success' : 'warning'" size="small">
              {{ row.type === 'autonomous' ? '自主分析' : '问答交互' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="200" />
        <el-table-column prop="duration" label="耗时" width="100">
          <template #default="{ row }">
            {{ row.duration }}秒
          </template>
        </el-table-column>
        <el-table-column label="内容">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loadingHistory && history.length === 0" description="暂无分析历史" />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="分析详情" width="80%">
      <pre class="analysis-content">{{ currentAnalysis?.summary }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { agentApi } from '../api'

const question = ref('')
const asking = ref(false)
const answer = ref('')

const autoEnabled = ref(false)
const analyzing = ref(false)
const lastResult = ref('')

const history = ref([])
const loadingHistory = ref(false)
const detailVisible = ref(false)
const currentAnalysis = ref(null)

const sendQuestion = async () => {
  if (!question.value.trim()) return
  asking.value = true
  answer.value = ''
  try {
    const { data } = await agentApi.chat(question.value.trim())
    answer.value = data.answer
  } catch (e) {
    ElMessage.error('问答失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    asking.value = false
  }
}

const toggleAutoMode = async () => {
  ElMessage.success(autoEnabled.value ? '已开启自主分析模式' : '已关闭自主分析模式')
}

const triggerAnalysis = async () => {
  analyzing.value = true
  lastResult.value = ''
  try {
    const { data } = await agentApi.triggerAnalysis()
    lastResult.value = data.result
    ElMessage.success('分析完成')
    await loadHistory()
  } catch (e) {
    ElMessage.error('分析失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    analyzing.value = false
  }
}

const loadHistory = async () => {
  loadingHistory.value = true
  try {
    const { data } = await agentApi.getHistory(10)
    history.value = data.history || []
  } catch (e) {
    console.error(e)
  } finally {
    loadingHistory.value = false
  }
}

const viewDetail = (analysis) => {
  currentAnalysis.value = analysis
  detailVisible.value = true
}

onMounted(loadHistory)
</script>

<style scoped>
.agent-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-input {
  margin-bottom: 8px;
}

.chat-answer {
  margin-top: 8px;
}

.answer-text {
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.7;
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  max-height: 500px;
  overflow-y: auto;
}

.analysis-result {
  margin-top: 8px;
}

.analysis-content {
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
  max-height: 600px;
  overflow-y: auto;
}
</style>