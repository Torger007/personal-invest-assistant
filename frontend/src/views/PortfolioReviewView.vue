<template>
  <div class="review-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">问 AI · 持仓复盘</p>
        <h2>持仓复盘记录</h2>
        <p class="subtitle">通过“问 AI”中的“帮我分析当前持仓”发起复盘，这里保存每次运行及其依据。</p>
      </div>
      <router-link class="history-link" to="/portfolio-reviews">查看全部历史</router-link>
    </header>

    <div class="review-layout">
      <aside class="history-panel" v-loading="historyLoading">
        <h3>历史复盘</h3>
        <p v-if="!historyLoading && !reviews.length" class="empty-copy">暂无复盘记录。打开“问 AI”，试试“帮我分析当前持仓”。</p>
        <router-link
          v-for="item in reviews"
          :key="item.id"
          class="history-item"
          :class="{ active: item.id === reviewId }"
          :to="{ name: 'PortfolioReviewDetail', params: { reviewId: item.id } }"
        >
          <span class="history-time">{{ formatTime(item.started_at) }}</span>
          <strong>{{ statusLabel(item) }}</strong>
          <small v-if="item.previous_review_id">与上次复盘比较</small>
          <small v-else>首次复盘或暂无可比较基线</small>
        </router-link>
      </aside>

      <main class="report-panel" v-loading="reportLoading">
        <div v-if="loadError" class="empty-state">
          <el-alert :title="loadError" type="error" :closable="false" show-icon />
        </div>
        <div v-else-if="!review" class="empty-state">
          <el-empty description="选择一条历史复盘查看报告" />
        </div>
        <template v-else>
          <div class="report-heading">
            <div>
              <p class="eyebrow">复盘编号 {{ review.id }}</p>
              <h3>当前持仓复盘</h3>
              <p class="muted">开始于 {{ formatTime(review.started_at) }}<span v-if="review.completed_at"> · 完成于 {{ formatTime(review.completed_at) }}</span></p>
            </div>
            <el-tag :type="statusTag(review)">{{ statusLabel(review) }}</el-tag>
          </div>

          <template v-if="review.status === 'running'">
            <el-alert title="复盘正在运行" description="正在核对持仓估值；按提问需要读取其他数据。完成后本页会自动更新。" type="info" :closable="false" show-icon />
          </template>
          <template v-else-if="review.status !== 'completed'">
            <el-alert :title="review.status === 'interrupted' ? '本次复盘已中断' : '本次复盘未完成'" :description="review.error || '可在问 AI 中重新发起。'" type="warning" :closable="false" show-icon />
          </template>
          <template v-else-if="review.result">
            <section class="report-section">
              <h4>数据截至时间</h4>
              <div class="asof-grid">
                <div><span>运行时间</span><strong>{{ formatTime(review.result.as_of?.run_at) }}</strong></div>
                <div><span>持仓估值</span><strong>{{ rangeLabel(review.result.as_of?.holdings) }}</strong></div>
                <div><span>基金净值</span><strong>{{ rangeLabel(review.result.as_of?.fund_nav) }}</strong></div>
                <div><span>市场数据</span><strong>{{ review.result.as_of?.market || '未读取（按需）' }}</strong></div>
                <div><span>规则建议</span><strong>{{ Object.keys(review.result.as_of?.advice || {}).length ? rangeLabel(review.result.as_of?.advice) : '未读取（按需）' }}</strong></div>
              </div>
            </section>

            <section class="report-section">
              <h4>最值得关注的事 <span class="section-count">{{ findings.length }} / 3</span></h4>
              <div v-for="(finding, index) in findings" :key="index" class="finding-card">
                <div class="finding-title">
                  <span class="finding-number">{{ index + 1 }}</span>
                  <h5>{{ finding.title }}</h5>
                  <el-tag size="small" :type="findingTag(finding.category)">{{ findingCategory(finding.category) }}</el-tag>
                </div>
                <p>{{ finding.importance }}</p>
                <p class="muted">与上次相比：{{ finding.relation_to_previous }}</p>
                <p class="muted">下一步观察：{{ finding.next_observation }}</p>
                <div class="evidence-chips">
                  <button v-for="id in finding.current_evidence_ids" :key="id" type="button" @click="scrollToEvidence(id)">
                    证据 · {{ evidenceLabel(evidenceById[id]) }}
                  </button>
                </div>
              </div>
              <p v-if="findings.length < 3" class="empty-slot">其余关注位置：暂无更多有证据支持的新变化。</p>
            </section>

            <section class="report-section">
              <div class="section-heading">
                <h4>与上次相比</h4>
                <router-link v-if="review.previous_review_id" :to="{ name: 'PortfolioReviewDetail', params: { reviewId: review.previous_review_id } }">查看上次报告</router-link>
              </div>
              <p v-if="review.result.comparison_status === 'first_review'" class="muted">暂无上次成功复盘可比较。</p>
              <p v-else-if="!changes.length" class="muted">本次没有可核对的变化；请查看数据限制。</p>
              <div v-for="(change, index) in changes" :key="index" class="change-row">
                <el-tag size="small" type="info">{{ changeCategory(change.kind) }}</el-tag>
                <div>
                  <p>{{ change.description }}</p>
                  <small>本次截至 {{ change.current_as_of }} · 上次截至 {{ change.previous_as_of }}</small>
                  <div class="evidence-chips">
                    <button v-for="id in change.current_evidence_ids" :key="'c' + id" type="button" @click="scrollToEvidence(id)">本次 · {{ evidenceLabel(evidenceById[id]) }}</button>
                    <button v-for="id in change.previous_evidence_ids" :key="'p' + id" type="button" @click="scrollToEvidence(id)">上次 · {{ evidenceLabel(evidenceById[id]) }}</button>
                  </div>
                </div>
              </div>
            </section>

            <section v-if="review.result.limitations?.length" class="report-section">
              <h4>{{ review.result.status === 'ready' ? '数据提示' : '数据限制' }}</h4>
              <ul class="limitations"><li v-for="(item, index) in review.result.limitations" :key="index">{{ item }}</li></ul>
              <div class="limitation-links">
                <router-link v-if="review.quality_report?.missing?.includes('get_latest_advice')" to="/advice">查看投资建议与生成入口</router-link>
                <router-link v-if="review.quality_report?.stale?.includes('get_portfolio')" to="/funds">核对持仓估值</router-link>
              </div>
            </section>

            <section class="report-section">
              <h4>证据记录</h4>
              <p class="muted">展开证据查看来源、实际日期与取数时间；持仓估值明细沿用持仓页的记录。</p>
              <div v-for="fact in citedEvidence" :id="evidenceDomId(fact.evidence_id)" :key="fact.evidence_id" class="evidence-card">
                <div class="evidence-heading">
                  <strong>{{ evidenceLabel(fact) }}</strong>
                  <router-link v-if="evidenceLink(fact)" :to="evidenceLink(fact)">查看来源</router-link>
                </div>
                <p>截至 {{ fact.as_of || '未知' }} · 读取于 {{ formatTime(fact.read_at) }}</p>
                <p v-if="fact.values?.position_id">
                  持有估值 ¥{{ Number(fact.values.market_value).toFixed(2) }} · 来源 {{ fact.source }}
                  <span v-if="fact.values.calibration_as_of"> · {{ fact.values.calibration_as_of }} 按{{ fact.values.calibration_basis === 'shares_times_nav' ? '净值推算' : '人工校准' }}</span>
                </p>
                <details>
                  <summary>查看证据详情</summary>
                  <dl>
                    <dt>证据 ID</dt><dd>{{ fact.evidence_id }}</dd>
                    <dt>来源</dt><dd>{{ fact.source }} · {{ fact.source_ref }}</dd>
                    <dt>单位 / 口径</dt><dd>{{ fact.unit }} · {{ fact.calculation_basis }}</dd>
                    <dt>记录值</dt><dd><pre>{{ JSON.stringify(fact.values, null, 2) }}</pre></dd>
                    <dt v-if="fact.quality_flags?.length">质量标记</dt><dd v-if="fact.quality_flags?.length">{{ fact.quality_flags.join('、') }}</dd>
                  </dl>
                </details>
              </div>
              <p v-if="!citedEvidence.length" class="muted">这份报告没有可展示的证据引用。</p>
            </section>
          </template>
        </template>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { agentApi } from '../api'

const route = useRoute()
const reviewId = computed(() => route.params.reviewId || null)
const reviews = ref([])
const review = ref(null)
const historyLoading = ref(false)
const reportLoading = ref(false)
const loadError = ref('')
let pollTimer = null
let loadSequence = 0

const findings = computed(() => (review.value?.result?.findings || []).slice(0, 3))
const changes = computed(() => review.value?.result?.changes_since_previous || [])
const evidenceById = computed(() => Object.fromEntries((review.value?.evidence_snapshot || []).map(fact => [fact.evidence_id, fact])))
const citedEvidence = computed(() => {
  const ids = new Set(review.value?.result?.evidence_ids || [])
  return (review.value?.evidence_snapshot || []).filter(fact => ids.has(fact.evidence_id) || fact.values?.position_id)
})

function formatTime(value) {
  if (!value) return '未知'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('zh-CN', { hour12: false })
}
function rangeLabel(values) {
  const dates = [...new Set(Object.values(values || {}).filter(Boolean))].sort()
  return dates.length ? (dates.length === 1 ? dates[0] : `${dates[0]} 至 ${dates.at(-1)}`) : '未知'
}
function statusLabel(item) {
  if (item.status === 'running') return '运行中'
  if (item.status === 'interrupted') return '已中断'
  if (item.status === 'failed') return '失败'
  return item.result_status === 'degraded' ? '已完成 · 数据受限' : '已完成'
}
function statusTag(item) {
  if (item.status === 'running') return 'info'
  if (item.status !== 'completed' || item.result_status === 'degraded') return 'warning'
  return 'success'
}
function findingCategory(category) {
  return { risk: '风险', change: '变化', data_to_verify: '待核实数据', watch: '保持关注' }[category] || category
}
function findingTag(category) {
  return { risk: 'danger', change: 'warning', data_to_verify: 'info', watch: 'success' }[category] || 'info'
}
function changeCategory(kind) {
  return { holding: '持仓变化', data: '数据变化', rule: '规则变化', continuity: '判断延续' }[kind] || kind
}
function evidenceLabel(fact) {
  if (!fact) return '证据记录'
  const values = fact.values || {}
  if (values.position_id) return `持仓 ${values.position_id}`
  if (fact.source_ref === 'derived:portfolio_composition') return '组合持仓快照'
  if (fact.source === 'rule_engine') return `规则建议 ${values.fund_code || ''}`.trim()
  if (values.code) return `市场指数 ${values.code}`
  if (values.fund_code) return `基金 ${values.fund_code}`
  if (fact.source === 'agent_runtime') return '运行与规则版本'
  return fact.source_ref || fact.evidence_id
}
function evidenceLink(fact) {
  if (!fact) return null
  const positionId = fact.values?.position_id || fact.source_ref?.match(/user_fund_positions:([^,]+)/)?.[1]
  if (positionId) return { path: '/funds', query: { positionId } }
  if (fact.source_ref === 'derived:portfolio_composition' || fact.source_ref === 'derived:portfolio_weight') return { path: '/funds' }
  if (fact.source === 'rule_engine' && fact.values?.fund_code) {
    const recordId = fact.source_ref?.match(/advice_records:(\d+)/)?.[1]
    return { path: '/advice', query: { fundCode: fact.values.fund_code, ...(recordId ? { recordId } : {}) } }
  }
  const runId = fact.source_ref?.match(/^portfolio_review_run:(.+)$/)?.[1]
  if (runId && runId !== 'unpersisted') return { name: 'PortfolioReviewDetail', params: { reviewId: runId } }
  return null
}
function evidenceDomId(id) { return `evidence-${id.replace(/[^a-zA-Z0-9_-]/g, '-')}` }
function scrollToEvidence(id) {
  document.getElementById(evidenceDomId(id))?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
async function loadHistory() {
  historyLoading.value = true
  try {
    reviews.value = (await agentApi.getPortfolioReviews(100)).data.reviews || []
  } catch {
    loadError.value = '加载复盘历史失败，请稍后重试。'
  } finally {
    historyLoading.value = false
  }
}
async function loadReview(id, showLoading = true) {
  const sequence = ++loadSequence
  if (showLoading) reportLoading.value = true
  loadError.value = ''
  try {
    const { data } = await agentApi.getPortfolioReview(id)
    if (sequence !== loadSequence) return
    review.value = data
    if (data.status !== 'running') {
      clearTimeout(pollTimer)
      pollTimer = null
      await loadHistory()
    }
  } catch (error) {
    if (sequence !== loadSequence) return
    review.value = null
    loadError.value = error.response?.status === 404 ? '复盘记录不存在或无权查看。' : '加载复盘报告失败，请稍后重试。'
  } finally {
    if (sequence === loadSequence) reportLoading.value = false
  }
}
function schedulePoll(id) {
  pollTimer = setTimeout(async () => {
    await loadReview(id, false)
    if (reviewId.value === id && review.value?.status === 'running') schedulePoll(id)
  }, 3000)
}
watch(reviewId, async id => {
  clearTimeout(pollTimer)
  pollTimer = null
  review.value = null
  loadError.value = ''
  if (!id) return
  await loadReview(id)
  if (reviewId.value === id && review.value?.status === 'running') schedulePoll(id)
}, { immediate: true })
onMounted(loadHistory)
onBeforeUnmount(() => { clearTimeout(pollTimer); loadSequence++ })
</script>

<style scoped>
.review-page { max-width: 1440px; margin: 0 auto; padding: 28px; }
.page-header { display: flex; justify-content: space-between; align-items: end; gap: 20px; margin-bottom: 24px; }
.eyebrow { margin: 0 0 7px; color: var(--color-accent); font-size: 12px; font-weight: 650; }
h2 { margin: 0; font-size: 28px; } h3, h4, h5 { margin: 0; }
.subtitle, .muted { color: var(--color-foreground-muted); }
.subtitle { margin: 8px 0 0; font-size: 14px; }
.history-link, .section-heading a, .evidence-heading a { color: var(--color-accent); text-decoration: none; font-size: 13px; }
.history-link:hover, .section-heading a:hover, .evidence-heading a:hover { text-decoration: underline; }
.review-layout { display: grid; grid-template-columns: 265px minmax(0, 1fr); gap: 20px; align-items: start; }
.history-panel, .report-panel { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 16px; }
.history-panel { min-height: 220px; padding: 16px; }
.history-panel h3 { margin: 2px 4px 14px; font-size: 16px; }
.history-item { display: flex; flex-direction: column; gap: 5px; padding: 12px; border-radius: 10px; color: var(--color-foreground); text-decoration: none; }
.history-item:hover, .history-item.active { background: var(--color-muted); }
.history-item.active { box-shadow: inset 3px 0 var(--color-accent); }
.history-item strong { font-size: 14px; }
.history-item small, .history-time, .empty-copy { color: var(--color-foreground-muted); font-size: 12px; }
.empty-copy { line-height: 1.7; }
.report-panel { min-height: 480px; padding: 24px; }
.empty-state { padding: 45px 10px; }
.report-heading { display: flex; align-items: start; justify-content: space-between; gap: 18px; padding-bottom: 22px; border-bottom: 1px solid var(--color-border); }
.report-heading h3 { font-size: 24px; }
.report-heading .muted { margin: 9px 0 0; font-size: 12px; }
.report-section { padding-top: 26px; }
.report-section h4 { margin-bottom: 14px; font-size: 18px; }
.section-count { color: var(--color-foreground-muted); font-size: 12px; font-weight: 400; }
.section-heading { display: flex; justify-content: space-between; align-items: baseline; }
.asof-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 10px; }
.asof-grid div { padding: 13px; background: var(--color-muted); border-radius: 10px; }
.asof-grid span, .asof-grid strong { display: block; }
.asof-grid span { color: var(--color-foreground-muted); font-size: 12px; }
.asof-grid strong { margin-top: 6px; font-size: 13px; }
.finding-card { margin-bottom: 12px; padding: 18px; border: 1px solid var(--color-border); border-radius: 12px; }
.finding-title { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.finding-title h5 { font-size: 16px; }
.finding-number { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 50%; background: var(--color-accent); color: white; font-size: 12px; }
.finding-card p { margin: 10px 0 0; line-height: 1.55; font-size: 14px; }
.finding-card .muted, .change-row small { font-size: 13px; }
.empty-slot { color: var(--color-foreground-muted); font-size: 13px; }
.evidence-chips { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 12px; }
.evidence-chips button { border: 1px solid var(--color-border); border-radius: 20px; background: var(--color-muted); padding: 5px 9px; color: var(--color-accent); font-size: 12px; cursor: pointer; }
.evidence-chips button:hover { text-decoration: underline; }
.change-row { display: flex; align-items: start; gap: 12px; padding: 14px 0; border-top: 1px solid var(--color-border); }
.change-row p { margin: 0 0 6px; font-size: 14px; }
.change-row small { color: var(--color-foreground-muted); }
.limitations { padding-left: 20px; color: var(--color-foreground-secondary); line-height: 1.7; }
.limitation-links { display: flex; flex-wrap: wrap; gap: 12px; }
.limitation-links a { color: var(--color-accent); font-size: 13px; text-decoration: none; }
.limitation-links a:hover { text-decoration: underline; }
.evidence-card { border: 1px solid var(--color-border); border-radius: 10px; padding: 13px; margin-top: 10px; scroll-margin-top: 20px; }
.evidence-heading { display: flex; justify-content: space-between; gap: 12px; }
.evidence-card p { color: var(--color-foreground-muted); margin: 7px 0; font-size: 12px; }
.evidence-card summary { cursor: pointer; color: var(--color-accent); font-size: 12px; }
.evidence-card dl { display: grid; grid-template-columns: 80px minmax(0, 1fr); gap: 8px; font-size: 12px; overflow-wrap: anywhere; }
.evidence-card dt { color: var(--color-foreground-muted); }.evidence-card dd { margin: 0; }
.evidence-card pre { white-space: pre-wrap; overflow-wrap: anywhere; margin: 0; }
@media (max-width: 780px) { .review-page { padding: 16px; }.page-header { align-items: start; flex-direction: column; }.review-layout { grid-template-columns: 1fr; }.history-panel { min-height: 0; }.report-panel { padding: 16px; } }
</style>
