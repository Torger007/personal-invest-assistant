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
        <ToolProgress v-if="asking || questionProgress.length" :items="questionProgress" />
        <DecisionCard v-if="questionDecision" :decision="questionDecision" />
        <pre class="answer-text">{{ answer }}</pre>
      </div>
      <ToolProgress v-else-if="asking" :items="questionProgress" />
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
        <ToolProgress v-if="analysisProgress.length" :items="analysisProgress" />
        <DecisionCard v-if="analysisDecision" :decision="analysisDecision" />
        <pre class="answer-text">{{ lastResult }}</pre>
      </div>
      <ToolProgress v-else-if="analyzing" :items="analysisProgress" />
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
import { defineComponent, h, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { agentApi } from '../api'

const question = ref('')
const asking = ref(false)
const answer = ref('')
const questionProgress = ref([])
const questionDecision = ref(null)

const autoEnabled = ref(false)
const analyzing = ref(false)
const lastResult = ref('')
const analysisProgress = ref([])
const analysisDecision = ref(null)

const history = ref([])
const loadingHistory = ref(false)
const detailVisible = ref(false)
const currentAnalysis = ref(null)

const sendQuestion = async () => {
  if (!question.value.trim()) return
  asking.value = true
  answer.value = ''
  questionProgress.value = []
  questionDecision.value = null
  try {
    await agentApi.chatStream(question.value.trim(), event => {
      applyAgentEvent(event, answer, questionProgress, questionDecision)
    })
  } catch (e) {
    ElMessage.error('问答失败: ' + e.message)
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
  analysisProgress.value = []
  analysisDecision.value = null
  try {
    const { data } = await agentApi.triggerAnalysis()
    await new Promise((resolve, reject) => {
      const source = agentApi.subscribeAnalysis(data.task_id, (event, currentSource) => {
        applyAgentEvent(event, lastResult, analysisProgress, analysisDecision)
        if (event.type === 'complete') {
          currentSource.close()
          ElMessage.success('分析完成')
          resolve()
        }
        if (event.type === 'error') {
          currentSource.close()
          reject(new Error(event.message))
        }
      })
      source.onerror = () => {
        source.close()
        reject(new Error('任务进度连接中断'))
      }
    })
    await loadHistory()
  } catch (e) {
    ElMessage.error('分析失败: ' + e.message)
  } finally {
    analyzing.value = false
  }
}

const toolLabels = {
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
  get_analysis_history: '正在读取历史判断'
}

const applyAgentEvent = (event, result, progress, decision) => {
  if (event.type === 'tool_started') {
    progress.value.push({ name: event.name, status: 'running' })
  } else if (event.type === 'tool_completed') {
    const item = [...progress.value].reverse().find(step => step.name === event.name && step.status === 'running')
    if (item) Object.assign(item, { status: event.status, duration: event.duration_ms, count: event.data_count })
  } else if (event.type === 'summarizing') {
    progress.value.push({ name: 'summarizing', status: 'running' })
  } else if (event.type === 'waiting' && event.stage === 'summarizing') {
    const item = progress.value.find(step => step.name === 'summarizing' && step.status === 'running')
    if (item) item.elapsed = event.elapsed_ms
  } else if (event.type === 'token') {
    result.value += event.content
  } else if (event.type === 'complete') {
    result.value = event.answer || result.value
    const item = progress.value.find(step => step.name === 'summarizing' && step.status === 'running')
    if (item) item.status = 'success'
  } else if (event.type === 'error') {
    progress.value.push({ name: 'error', status: 'error', message: event.message })
  } else if ((event.type === 'decision_ready' || event.type === 'degraded') && event.decision) {
    decision.value = event.decision
  }
}

const DecisionCard = defineComponent({
  props: { decision: { type: Object, required: true } },
  setup(props) {
    return () => h('div', { class: ['decision-card', props.decision.status] }, [
      h('div', { class: 'decision-title' }, '规则引擎决策'),
      h('div', { class: 'decision-action' }, props.decision.action),
      props.decision.target_position != null
        ? h('div', { class: 'decision-meta' }, `目标仓位 ${(props.decision.target_position * 100).toFixed(0)}%`)
        : null,
      props.decision.confidence != null
        ? h('div', { class: 'decision-meta' }, `置信度 ${props.decision.confidence}%`)
        : null,
      props.decision.blocking_reasons?.length
        ? h('div', { class: 'decision-reasons' }, props.decision.blocking_reasons.join('；'))
        : null,
      h('div', { class: 'decision-version' }, `规则版本：${props.decision.rule_version}`),
    ])
  }
})

const ToolProgress = defineComponent({
  props: { items: { type: Array, default: () => [] } },
  setup(props) {
    return () => h('div', { class: 'tool-progress' }, props.items.map(item => h('div', {
      class: ['tool-step', item.status]
    }, [
      h('span', { class: 'tool-step-state' }, item.status === 'running' ? '...' : item.status === 'success' ? '✓' : '!'),
      h('span', { class: 'tool-step-label' }, item.name === 'summarizing'
        ? `正在生成结论${item.elapsed ? `，已等待 ${Math.ceil(item.elapsed / 1000)} 秒` : ''}`
        : item.name === 'error' ? item.message : toolLabels[item.name] || item.name),
      item.duration !== undefined ? h('span', { class: 'tool-step-meta' }, `${item.duration} ms${item.count != null ? ` · ${item.count} 条` : ''}`) : null
    ])))
  }
})

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

.tool-progress {
  margin: 12px 0;
  border-left: 2px solid #dcdfe6;
  padding-left: 12px;
}

.tool-step {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 28px;
  color: #606266;
  font-size: 13px;
}

.tool-step-state {
  width: 16px;
  color: #909399;
  text-align: center;
}

.tool-step.running .tool-step-state { color: #409eff; }
.tool-step.success .tool-step-state { color: #67c23a; }
.tool-step.error .tool-step-state { color: #f56c6c; }

.tool-step-meta {
  color: #909399;
  font-size: 12px;
}

.analysis-content {
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
  max-height: 600px;
  overflow-y: auto;
}

.decision-card {
  margin: 12px 0;
  padding: 14px 16px;
  border: 1px solid #dcdfe6;
  border-left: 4px solid #409eff;
  border-radius: 6px;
  background: #f5f7fa;
}

.decision-card.degraded,
.decision-card.blocked {
  border-left-color: #e6a23c;
  background: #fdf6ec;
}

.decision-title { font-size: 12px; color: #909399; }
.decision-action { margin: 4px 0; font-size: 18px; font-weight: 600; }
.decision-meta, .decision-version { display: inline-block; margin-right: 12px; font-size: 13px; color: #606266; }
.decision-reasons { margin-top: 8px; font-size: 13px; color: #e6a23c; }
</style>
