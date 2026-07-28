<template>
  <div class="advice-report">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h2>投资建议</h2>
        <span class="header-subtitle" v-if="adviceDate">更新于 {{ adviceDate }}</span>
      </div>
      <div class="header-actions">
        <el-tag v-if="marketEnv" :type="envTagType(marketEnv)" size="small" class="env-tag">
          {{ marketEnv }}
        </el-tag>
        <el-button type="primary" :loading="generating" @click="handleGenerate">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 12.728l-.707.707M12 21v-1m4.95-2.05l.707.707M4.95 4.95l.707.707"/>
          </svg>
          生成建议
        </el-button>
      </div>
    </div>

    <el-alert
      title="本系统仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
      type="warning"
      :closable="false"
      class="warning-alert"
    >
      <template #icon>
        <svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <path d="M12 9v4M12 17h.01"/>
        </svg>
      </template>
    </el-alert>

    <div v-loading="loading" class="page-body">
      <!-- 统计指示卡 -->
      <div class="stats-row" v-if="summary">
        <div class="stat-card">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2"/>
              <path d="M8 21h8M12 17v4"/>
            </svg>
          </div>
          <div class="stat-body">
            <div class="stat-label">持仓基金</div>
            <div class="stat-value mono">{{ summary.total_funds }}</div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div class="stat-body">
            <div class="stat-label">平均置信度</div>
            <div class="stat-value mono">{{ summary.avg_confidence }}%</div>
            <div class="stat-bar">
              <div class="stat-bar-fill" :style="{ width: summary.avg_confidence + '%' }"></div>
            </div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M7 7l9.2 9.2M17 7v10H7"/>
            </svg>
          </div>
          <div class="stat-body">
            <div class="stat-label">多空信号</div>
            <div class="stat-signals">
              <el-tag size="small" type="success" v-if="summary.bullish_count">{{ summary.bullish_count }}看多</el-tag>
              <el-tag size="small" type="danger" v-if="summary.bearish_count">{{ summary.bearish_count }}看空</el-tag>
              <el-tag size="small" type="info" v-if="summary.neutral_count">{{ summary.neutral_count }}中性</el-tag>
              <span v-if="!summary.bullish_count && !summary.bearish_count && !summary.neutral_count" class="stat-na">暂无</span>
            </div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 3v18h18"/>
              <path d="M7 16l4-4 4 4 5-6"/>
            </svg>
          </div>
          <div class="stat-body">
            <div class="stat-label">市场环境</div>
            <div class="stat-value">
              <el-tag :type="envTagType(marketEnv)" size="small">{{ marketEnv || '--' }}</el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 基金建议卡片网格 -->
      <div class="fund-grid" v-if="portfolioFunds.length">
        <div
          v-for="f in portfolioFunds"
          :key="f.fund_code"
          class="fund-card"
          :class="{ 'no-advice': !f.latest_advice }"
        >
          <div class="fund-card-header">
            <el-tag
              :type="signalTagType(f.latest_advice?.overall_signal)"
              size="small"
              class="signal-badge"
            >
              {{ f.latest_advice?.overall_signal || '暂无建议' }}
            </el-tag>
            <span class="fund-weight">{{ (f.weight * 100).toFixed(0) }}%</span>
          </div>

          <div class="fund-card-body">
            <div class="fund-name" :title="f.fund_name">{{ f.fund_name }}</div>
            <div class="fund-code mono">{{ f.fund_code }}</div>

            <div v-if="f.latest_advice" class="confidence-section">
              <div class="confidence-label">
                <span>置信度</span>
                <span class="mono">{{ f.latest_advice.confidence ?? '--' }}%</span>
              </div>
              <div class="confidence-bar">
                <div
                  class="confidence-fill"
                  :style="{ width: (f.latest_advice.confidence ?? 0) + '%' }"
                ></div>
              </div>
            </div>

            <div v-if="f.latest_advice?.scores" class="scores-mini">
              <div class="score-dot">
                <span class="score-dot-label">技术</span>
                <span class="score-dot-value mono">{{ f.latest_advice.scores.technical ?? '--' }}</span>
              </div>
              <div class="score-dot">
                <span class="score-dot-label">估值</span>
                <span class="score-dot-value mono">{{ f.latest_advice.scores.valuation ?? '--' }}</span>
              </div>
              <div class="score-dot">
                <span class="score-dot-label">资金</span>
                <span class="score-dot-value mono">{{ f.latest_advice.scores.fund_flow ?? '--' }}</span>
              </div>
              <div class="score-dot">
                <span class="score-dot-label">情绪</span>
                <span class="score-dot-value mono">{{ f.latest_advice.scores.sentiment ?? '--' }}</span>
              </div>
            </div>
          </div>

          <div class="fund-card-actions">
            <el-button
              size="small"
              :disabled="!f.latest_advice"
              @click="openDetail(f.fund_code, f.fund_name)"
              class="detail-btn"
            >
              <svg class="btn-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              详情
            </el-button>
          </div>
        </div>
      </div>

      <el-empty v-if="!loading && !portfolioFunds.length" description="暂无建议数据，请先点击「生成建议」" />

      <!-- 图表区域 -->
      <div v-if="hasHistory" class="charts-section">
        <!-- 综合评分趋势 -->
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <div class="card-title">
                <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 3v18h18"/>
                  <path d="M7 14l4-4 4 4 5-6"/>
                </svg>
                综合评分趋势
              </div>
              <span class="card-badge">多基金叠加</span>
            </div>
          </template>
          <div class="chart-wrapper">
            <div ref="trendChartRef" class="chart-container"></div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="detailFundName || '建议详情'"
      width="820px"
      class="detail-dialog"
      destroy-on-close
    >
      <div v-if="detail" class="advice-detail">
        <!-- 元数据头 -->
        <div class="detail-header">
          <div class="detail-meta">
            <div class="meta-item">
              <span class="meta-label">基金代码</span>
              <span class="meta-value mono">{{ detail.fund_code }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">日期</span>
              <span class="meta-value mono">{{ detail.date }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">操作建议</span>
              <el-tag :type="signalTagType(detail.overall_signal)" class="signal-tag-lg">
                {{ detail.overall_signal }}
              </el-tag>
            </div>
            <div class="meta-item">
              <span class="meta-label">置信度</span>
              <span class="meta-value mono">{{ detail.confidence }}%</span>
            </div>
          </div>
        </div>

        <!-- 雷达图 + 趋势图并排 -->
        <div class="detail-charts-row">
          <div class="detail-chart-half">
            <h4 class="section-title">维度评分雷达</h4>
            <div ref="radarChartRef" class="radar-container"></div>
          </div>
          <div class="detail-chart-half">
            <h4 class="section-title">历史评分趋势</h4>
            <div ref="detailTrendRef" class="radar-container"></div>
          </div>
        </div>

        <!-- 分维度详情 -->
        <div class="dimensions-section">
          <h4 class="section-title">各维度分析</h4>
          <div class="dimensions-grid">
            <div
              v-for="dim in dimensions"
              :key="dim.key"
              class="dimension-card"
              :class="dim.signalClass"
            >
              <div class="dim-header">
                <span class="dim-name">{{ dim.label }}</span>
                <el-tag :type="dim.tagType" size="small">{{ dim.signal }}</el-tag>
                <span class="dim-conf mono">{{ dim.confidence }}%</span>
              </div>
              <div class="dim-reasons">
                <p v-for="(r, ri) in dim.reasons" :key="ri">{{ r }}</p>
                <p v-if="!dim.reasons?.length" class="dim-na">暂无详细理由</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 完整建议原文（折叠） -->
        <el-collapse class="advice-collapse">
          <el-collapse-item title="完整建议原文" name="advice-text">
            <pre class="advice-raw">{{ detail.advice_text || '暂无' }}</pre>
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { adviceApi } from '../api'

// ============== 状态 ==============
const loading = ref(false)
const generating = ref(false)
const portfolioFunds = ref([])
const summary = ref(null)
const marketEnv = ref(null)
const adviceDate = ref(null)
const fundHistories = ref({})  // { fund_code: [records] }

// 详情弹窗
const detailVisible = ref(false)
const detail = ref(null)
const detailFundName = ref('')

// 图表 refs
const trendChartRef = ref(null)
const radarChartRef = ref(null)
const detailTrendRef = ref(null)
let trendChart = null
let radarChart = null
let detailTrendChart = null

// ============== 计算属性 ==============
const hasHistory = computed(() => {
  return Object.values(fundHistories.value).some(arr => arr.length > 1)
})

const dimensions = computed(() => {
  if (!detail.value) return []
  const scores = detail.value.scores || {}
  const details = detail.value.details || {}
  return [
    {
      key: 'technical', label: '技术面',
      score: scores.technical, signal: details.technical?.signal || '--',
      confidence: details.technical?.confidence ? (details.technical.confidence * 100).toFixed(0) : '--',
      reasons: details.technical?.reasons || [],
      tagType: signalTagType(details.technical?.signal),
      signalClass: signalTagType(details.technical?.signal),
    },
    {
      key: 'valuation', label: '估值面',
      score: scores.valuation, signal: details.valuation?.signal || '--',
      confidence: details.valuation?.confidence ? (details.valuation.confidence * 100).toFixed(0) : '--',
      reasons: details.valuation?.reasons || [],
      tagType: signalTagType(details.valuation?.signal),
      signalClass: signalTagType(details.valuation?.signal),
    },
    {
      key: 'fund_flow', label: '资金面',
      score: scores.fund_flow, signal: details.fund_flow?.signal || '--',
      confidence: details.fund_flow?.confidence ? (details.fund_flow.confidence * 100).toFixed(0) : '--',
      reasons: details.fund_flow?.reasons || [],
      tagType: signalTagType(details.fund_flow?.signal),
      signalClass: signalTagType(details.fund_flow?.signal),
    },
    {
      key: 'sentiment', label: '情绪面',
      score: scores.sentiment, signal: details.sentiment?.signal || '--',
      confidence: details.sentiment?.confidence ? (details.sentiment.confidence * 100).toFixed(0) : '--',
      reasons: details.sentiment?.reasons || [],
      tagType: signalTagType(details.sentiment?.signal),
      signalClass: signalTagType(details.sentiment?.signal),
    },
  ]
})

// ============== 辅助函数 ==============
const signalTagType = (signal) => {
  if (!signal) return 'info'
  if (signal.includes('加仓')) return 'success'
  if (signal.includes('止盈') || signal.includes('减仓')) return 'danger'
  return 'warning'
}

const envTagType = (env) => {
  if (!env) return 'info'
  if (env === '牛市') return 'danger'
  if (env === '熊市') return 'success'
  return 'warning'
}

const FUND_COLORS = ['#1E40AF', '#D97706', '#DC2626', '#16A34A', '#0284C7', '#7C3AED']
const FUND_NAMES = {}

// ============== 数据加载 ==============
const loadData = async () => {
  loading.value = true
  try {
    const { data } = await adviceApi.getPortfolio()
    portfolioFunds.value = data.funds || []
    summary.value = data.summary || null
    marketEnv.value = data.market_environment || null
    adviceDate.value = data.summary?.advice_date || null

    // 加载每只基金的历史数据
    fundHistories.value = {}
    const codes = (data.funds || []).map(f => f.fund_code)
    for (const code of codes) {
      try {
        const hRes = await adviceApi.getHistory(code, 60)
        fundHistories.value[code] = hRes.data.records || []
      } catch { /* ignore */ }
    }

    await nextTick()
    drawTrendChart()
  } catch (e) {
    console.error('加载建议数据失败', e)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const handleGenerate = async () => {
  generating.value = true
  try {
    await adviceApi.generate()
    ElMessage.success('建议生成完成')
    await loadData()
  } catch (e) {
    ElMessage.error('建议生成失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    generating.value = false
  }
}

const openDetail = async (code, name) => {
  detailFundName.value = name
  try {
    const { data } = await adviceApi.getFundAdvice(code)
    detail.value = data
    detailVisible.value = true
    await nextTick()
    drawRadarChart()
    drawDetailTrend(code)
  } catch (e) {
    ElMessage.error('加载详情失败')
  }
}

// ============== 趋势图（多基金叠加） ==============
const drawTrendChart = () => {
  if (!trendChartRef.value) return
  const entries = Object.entries(fundHistories.value).filter(([, records]) => records.length > 1)
  if (!entries.length) return

  if (!trendChart) trendChart = echarts.init(trendChartRef.value)

  // 收集所有日期
  const allDates = new Set()
  const seriesData = []
  entries.forEach(([code, records], idx) => {
    const rev = [...records].reverse()
    rev.forEach(r => allDates.add(r.date))
    seriesData.push({
      name: code,
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 2, color: FUND_COLORS[idx % FUND_COLORS.length] },
      data: rev.map(r => r.overall_score ?? null),
    })
  })

  const sortedDates = [...allDates].sort()

  // 参考线（顾问操作阈值）
  const markLines = [
    { yAxis: 75, label: { formatter: '强烈加仓' } },
    { yAxis: 60, label: { formatter: '适度加仓' } },
    { yAxis: 40, label: { formatter: '持有观望' } },
    { yAxis: 25, label: { formatter: '适度减仓' } },
  ]

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(30, 41, 59, 0.9)',
      borderColor: 'transparent',
      textStyle: { color: '#fff' },
    },
    legend: {
      data: seriesData.map(s => s.name),
      textStyle: { color: 'var(--color-foreground-secondary)', fontSize: 11 },
      top: 0,
    },
    grid: { left: '3%', right: '3%', bottom: '12%', top: '16%', containLabel: true },
    xAxis: {
      type: 'category',
      data: sortedDates,
      axisLine: { lineStyle: { color: 'var(--color-border)' } },
      axisLabel: { color: 'var(--color-foreground-muted)', fontSize: 11, rotate: 30 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { show: false },
      axisLabel: { color: 'var(--color-foreground-muted)', fontSize: 11 },
      splitLine: { lineStyle: { color: 'var(--color-border)', type: 'dashed' } },
      // 参考线
      splitArea: {
        show: true,
        areaStyle: {
          color: [
            'rgba(22, 163, 74, 0.04)',   // 75-100 加仓区
            'rgba(22, 163, 74, 0.02)',   // 60-75
            'rgba(234, 179, 8, 0.02)',   // 40-60 观望区
            'rgba(220, 38, 38, 0.02)',   // 25-40 减仓区
            'rgba(220, 38, 38, 0.04)',   // 0-25 止盈区
          ],
        },
      },
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 20, bottom: 5, borderColor: 'var(--color-border)' },
    ],
    series: seriesData,
  })
}

// ============== 雷达图 ==============
const drawRadarChart = () => {
  if (!radarChartRef.value || !detail.value) return
  if (!radarChart) radarChart = echarts.init(radarChartRef.value)

  const s = detail.value.scores || {}
  const values = [s.technical, s.valuation, s.fund_flow, s.sentiment].map(v => v ?? 0)

  radarChart.setOption({
    tooltip: {
      backgroundColor: 'rgba(30, 41, 59, 0.9)',
      borderColor: 'transparent',
      textStyle: { color: '#fff' },
    },
    radar: {
      indicator: [
        { name: '技术面', max: 100 },
        { name: '估值面', max: 100 },
        { name: '资金面', max: 100 },
        { name: '情绪面', max: 100 },
      ],
      shape: 'circle',
      center: ['50%', '50%'],
      radius: '65%',
      axisName: {
        color: 'var(--color-foreground-secondary)',
        fontSize: 12,
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(30, 64, 175, 0.02)', 'rgba(30, 64, 175, 0.06)'],
        },
      },
      splitLine: {
        lineStyle: { color: 'var(--color-border)' },
      },
    },
    series: [{
      type: 'radar',
      data: [{
        value: values,
        name: detail.value.fund_code,
        areaStyle: { color: 'rgba(30, 64, 175, 0.15)' },
        lineStyle: { color: '#1E40AF', width: 2 },
        itemStyle: { color: '#1E40AF' },
      }],
    }],
  })
}

// ============== 单基金历史趋势图 ==============
const drawDetailTrend = (code) => {
  if (!detailTrendRef.value) return
  const records = fundHistories.value[code]
  if (!records || records.length < 2) return

  if (!detailTrendChart) detailTrendChart = echarts.init(detailTrendRef.value)

  const rev = [...records].reverse()
  const dates = rev.map(r => r.date)

  detailTrendChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(30, 41, 59, 0.9)',
      borderColor: 'transparent',
      textStyle: { color: '#fff' },
      formatter: (params) => {
        const p = params[0]
        let html = `<div style="font-weight:600">${p.axisValue}</div>`
        params.forEach(pp => {
          html += `<div>${pp.marker} ${pp.seriesName}: ${pp.value}</div>`
        })
        return html
      },
    },
    legend: {
      data: ['综合评分', '技术面', '估值面', '资金面', '情绪面'],
      textStyle: { color: 'var(--color-foreground-secondary)', fontSize: 10 },
      top: 0,
    },
    grid: { left: '3%', right: '3%', bottom: '8%', top: '18%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'var(--color-border)' } },
      axisLabel: { color: 'var(--color-foreground-muted)', fontSize: 10, rotate: 30 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { show: false },
      axisLabel: { color: 'var(--color-foreground-muted)', fontSize: 10 },
      splitLine: { lineStyle: { color: 'var(--color-border)', type: 'dashed' } },
    },
    series: [
      {
        name: '综合评分',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#1E40AF' },
        data: rev.map(r => r.overall_score ?? null),
      },
      {
        name: '技术面',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: '#D97706', type: 'dashed' },
        data: rev.map(r => r.scores?.technical ?? null),
      },
      {
        name: '估值面',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: '#16A34A', type: 'dashed' },
        data: rev.map(r => r.scores?.valuation ?? null),
      },
      {
        name: '资金面',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: '#0284C7', type: 'dashed' },
        data: rev.map(r => r.scores?.fund_flow ?? null),
      },
      {
        name: '情绪面',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: '#7C3AED', type: 'dashed' },
        data: rev.map(r => r.scores?.sentiment ?? null),
      },
    ],
  })
}

// ============== 响应式 ==============
const resizeAll = () => {
  trendChart?.resize()
  radarChart?.resize()
  detailTrendChart?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', resizeAll)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeAll)
  trendChart?.dispose()
  radarChart?.dispose()
  detailTrendChart?.dispose()
})
</script>

<style scoped>
.advice-report {
  padding: var(--spacing-lg);
  max-width: 1400px;
  margin: 0 auto;
}

/* === Page Header === */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-md);
}

.page-header h2 {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-foreground);
}

.header-subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-foreground-muted);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.env-tag {
  font-size: var(--font-size-sm);
  padding: 4px 12px;
  border-radius: var(--radius-full);
}

.btn-icon {
  width: 16px;
  height: 16px;
  margin-right: 6px;
}

/* === Warning === */
.warning-alert {
  margin-bottom: var(--spacing-lg);
  border-radius: var(--radius-md);
}

.alert-icon {
  width: 20px;
  height: 20px;
}

/* === Page Body === */
.page-body {
  min-height: 200px;
}

/* === Stats Row === */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.stat-card {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: all var(--transition-fast);
}

.stat-card:hover {
  border-color: var(--color-primary-light);
  box-shadow: var(--shadow-sm);
}

.stat-icon {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-muted);
  border-radius: var(--radius-md);
  color: var(--color-primary);
}

.stat-icon svg {
  width: 22px;
  height: 22px;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-foreground-muted);
  margin-bottom: 4px;
}

.stat-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-foreground);
}

.stat-bar {
  height: 4px;
  background: var(--color-muted);
  border-radius: var(--radius-full);
  margin-top: 6px;
  overflow: hidden;
}

.stat-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  border-radius: var(--radius-full);
  transition: width var(--transition-normal);
}

.stat-signals {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.stat-signals .el-tag {
  border-radius: var(--radius-full);
}

.stat-na {
  font-size: var(--font-size-sm);
  color: var(--color-foreground-muted);
}

/* === Fund Cards Grid === */
.fund-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.fund-card {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  transition: all var(--transition-fast);
}

.fund-card:hover {
  border-color: var(--color-primary-light);
  box-shadow: var(--shadow-sm);
  transform: translateY(-2px);
}

.fund-card.no-advice {
  opacity: 0.6;
}

.fund-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.signal-badge {
  border-radius: var(--radius-full);
}

.fund-weight {
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--color-foreground-muted);
  background: var(--color-muted);
  padding: 2px 10px;
  border-radius: var(--radius-full);
}

.fund-card-body {
  flex: 1;
}

.fund-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-foreground);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

.fund-code {
  font-size: var(--font-size-xs);
  color: var(--color-foreground-muted);
  margin-bottom: var(--spacing-md);
}

/* Confidence in card */
.confidence-section {
  margin-bottom: var(--spacing-md);
}

.confidence-label {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--color-foreground-muted);
  margin-bottom: 4px;
}

.confidence-bar {
  height: 6px;
  background: var(--color-muted);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  border-radius: var(--radius-full);
  transition: width var(--transition-normal);
}

/* Mini scores grid */
.scores-mini {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}

.score-dot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  background: var(--color-muted);
  border-radius: var(--radius-sm);
}

.score-dot-label {
  font-size: var(--font-size-xs);
  color: var(--color-foreground-muted);
}

.score-dot-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-foreground);
}

.fund-card-actions {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border-light);
  text-align: center;
}

.detail-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.btn-icon-sm {
  width: 14px;
  height: 14px;
}

/* === Charts Section === */
.charts-section {
  margin-bottom: var(--spacing-lg);
}

.chart-card {
  margin-bottom: var(--spacing-lg);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-weight: var(--font-weight-semibold);
}

.card-icon {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.card-badge {
  font-size: var(--font-size-xs);
  padding: 4px 10px;
  background: var(--color-muted);
  border-radius: var(--radius-full);
  color: var(--color-foreground-secondary);
}

.chart-wrapper {
  background: linear-gradient(180deg, var(--color-surface), var(--color-muted));
  border-radius: var(--radius-md);
  padding: var(--spacing-sm);
}

.chart-container {
  height: 380px;
}

/* === Detail Dialog === */
.detail-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.advice-detail {
  padding: var(--spacing-lg);
}

.detail-header {
  margin-bottom: var(--spacing-lg);
}

.detail-meta {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
}

.meta-item {
  text-align: center;
  padding: var(--spacing-md);
  background: var(--color-muted);
  border-radius: var(--radius-md);
}

.meta-label {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-foreground-muted);
  margin-bottom: var(--spacing-xs);
}

.meta-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-foreground);
}

.signal-tag-lg {
  font-size: var(--font-size-base);
  padding: 4px 12px;
}

/* Radar + Trend side by side */
.detail-charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.detail-chart-half {
  background: var(--color-muted);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
}

.radar-container {
  height: 260px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin: 0 0 var(--spacing-md) 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-foreground);
}

/* Dimensions breakdown */
.dimensions-section {
  margin-bottom: var(--spacing-lg);
}

.dimensions-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-md);
}

.dimension-card {
  padding: var(--spacing-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.dim-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.dim-name {
  font-weight: var(--font-weight-semibold);
  color: var(--color-foreground);
}

.dim-conf {
  margin-left: auto;
  font-size: var(--font-size-sm);
  color: var(--color-foreground-secondary);
}

.dim-reasons p {
  margin: 4px 0;
  font-size: var(--font-size-xs);
  color: var(--color-foreground-secondary);
  line-height: var(--line-height-relaxed);
  padding-left: var(--spacing-sm);
  border-left: 2px solid var(--color-border);
}

.dim-na {
  font-style: italic;
  color: var(--color-foreground-muted);
}

/* Signal coloring for dimension cards */
.dimension-card.success { border-left-color: var(--color-success); }
.dimension-card.danger { border-left-color: var(--color-destructive); }
.dimension-card.warning { border-left-color: var(--color-accent); }

.dim-reasons p {
  border-left-color: var(--color-border);
}

/* Collapse */
.advice-collapse {
  margin-top: var(--spacing-md);
}

.advice-raw {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  white-space: pre-wrap;
  line-height: var(--line-height-relaxed);
  color: var(--color-foreground-secondary);
  max-height: 300px;
  overflow-y: auto;
  margin: 0;
}

/* === Mono === */
.mono {
  font-family: var(--font-mono);
}

/* === Responsive === */
@media (max-width: 1024px) {
  .fund-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .detail-charts-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .fund-grid {
    grid-template-columns: 1fr;
  }

  .detail-meta {
    grid-template-columns: repeat(2, 1fr);
  }

  .dimensions-grid {
    grid-template-columns: 1fr;
  }

  .detail-charts-row {
    grid-template-columns: 1fr;
  }
}
</style>
