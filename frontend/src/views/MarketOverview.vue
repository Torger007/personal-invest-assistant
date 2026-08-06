<template>
  <div class="market-overview">
    <div class="page-header">
      <h2>市场概览</h2>
      <div class="actions">
        <el-button type="primary" :loading="refreshing" @click="handleRefresh">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 0 1-9 9m9-9a9 9 0 0 0-9-9m9 9H3m9 9a9 9 0 0 1-9-9m9 9c1.66 0 3-4.03 3-9s-1.34-9-3-9m0 18c-1.66 0-3-4.03-3-9s1.34-9 3-9m-9 9a9 9 0 0 1 9-9"/>
          </svg>
          采集数据
        </el-button>
        <el-button @click="loadData">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 任务状态提示 -->
    <el-alert
      v-if="taskStatus"
      :title="taskStatusMessage"
      type="info"
      :closable="false"
      class="status-alert"
    >
      <template #icon>
        <svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 6v6l4 2"/>
        </svg>
      </template>
    </el-alert>

    <!-- 指数卡片 -->
    <div class="indices-grid">
      <el-card
        v-for="item in indices"
        :key="item.code"
        shadow="hover"
        class="index-card"
        @click="goIndexDetail(item.code)"
      >
        <div class="index-header">
          <div class="index-name">{{ item.name }}</div>
          <div class="index-date">{{ item.date || '--' }}</div>
        </div>
        <div class="index-body">
          <div class="index-value" :class="changeClass(item.change_pct)">
            {{ item.value ? item.value.toFixed(2) : '--' }}
          </div>
          <div class="index-change" :class="changeClass(item.change_pct)">
            <svg v-if="item.change_pct > 0" class="change-icon up" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 4l8 8h-6v8h-4v-8H4l8-8z"/>
            </svg>
            <svg v-else-if="item.change_pct < 0" class="change-icon down" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 20l-8-8h6V4h4v8h6l-8 8z"/>
            </svg>
            <span class="change-text">
              {{ formatChange(item.change, item.change_pct) }}
            </span>
          </div>
        </div>
        <div class="index-footer">
          <div class="mini-chart" :class="changeClass(item.change_pct)">
            <svg viewBox="0 0 100 30" preserveAspectRatio="none">
              <path v-if="item.change_pct >= 0" d="M0,25 L20,20 L40,15 L60,18 L80,10 L100,5" fill="none" stroke="currentColor" stroke-width="2"/>
              <path v-else d="M0,5 L20,10 L40,8 L60,15 L80,18 L100,25" fill="none" stroke="currentColor" stroke-width="2"/>
            </svg>
          </div>
        </div>
      </el-card>
    </div>

    <!-- AI 快捷入口卡片 -->
    <div class="ai-quick-card" @click="openAiDrawer">
      <div class="ai-quick-content">
        <div class="ai-quick-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
            <path d="M12 2a10 10 0 0 1 10 10"/>
            <circle cx="12" cy="12" r="4"/>
          </svg>
        </div>
        <div class="ai-quick-text">
          <h3>AI 投资助手</h3>
          <p>获取个性化投资建议 · 分析基金走势</p>
        </div>
      </div>
      <div class="ai-quick-arrow">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12h14M12 5l7 7-7 7"/>
        </svg>
      </div>
    </div>

    <!-- 资金流向 -->
    <el-card class="fund-flow-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
            <span>资金流向</span>
          </div>
          <span class="card-date">{{ fundFlow?.date || '--' }}</span>
        </div>
      </template>

      <div v-if="fundFlow" class="fund-flow-grid">
        <div class="flow-item">
          <div class="flow-label">
            <svg class="flow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10 17l5-5-5-5"/>
              <path d="M3 12h12"/>
            </svg>
            北向资金
          </div>
          <div class="flow-value" :class="flowClass(fundFlow.north_flow)">
            {{ formatFlow(fundFlow.north_flow) }}
          </div>
          <div class="flow-desc">外资净买入</div>
        </div>
        <div class="flow-divider"></div>
        <div class="flow-item">
          <div class="flow-label">
            <svg class="flow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 12H8M14 6l-6 6 6 6"/>
            </svg>
            主力资金
          </div>
          <div class="flow-value" :class="flowClass(fundFlow.main_flow)">
            {{ formatFlow(fundFlow.main_flow) }}
          </div>
          <div class="flow-desc">机构净流入</div>
        </div>
      </div>

      <el-empty v-else description="暂无资金流向数据，请先采集" />
    </el-card>

    <!-- 上证指数走势图 -->
    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 3v18h18"/>
              <path d="M7 12l4-4 4 4 5-6"/>
            </svg>
            <span>上证指数走势</span>
          </div>
          <span class="card-badge">近30日</span>
        </div>
      </template>
      <div class="chart-wrapper">
        <div ref="chartRef" class="chart-container"></div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { marketApi, taskApi } from '../api'

const emit = defineEmits(['open-ai-drawer'])

const router = useRouter()
const indices = ref([])
const fundFlow = ref(null)
const refreshing = ref(false)
const taskStatus = ref(null)
const chartRef = ref(null)
let chart = null

const taskStatusMessage = computed(() => {
  if (!taskStatus.value) return ''
  if (taskStatus.value.running) return '正在采集数据...'
  if (taskStatus.value.last_result === 'success') return '上次采集成功'
  if (taskStatus.value.last_result?.startsWith('failed')) return `采集失败: ${taskStatus.value.last_result}`
  return '每日16:30自动采集（周一至周五）'
})

const changeClass = (pct) => {
  if (pct === null || pct === undefined) return ''
  return pct > 0 ? 'up' : pct < 0 ? 'down' : ''
}

const flowClass = (val) => {
  if (val === null || val === undefined) return ''
  return val > 0 ? 'up' : val < 0 ? 'down' : ''
}

const formatChange = (change, pct) => {
  if (change === null || change === undefined) return '--'
  const sign = change >= 0 ? '+' : ''
  return `${sign}${change.toFixed(2)} (${sign}${pct.toFixed(2)}%)`
}

const formatFlow = (val) => {
  if (val === null || val === undefined) return '--'
  const yi = val / 1e8
  const sign = val >= 0 ? '+' : ''
  return `${sign}${yi.toFixed(2)} 亿`
}

const loadData = async () => {
  try {
    const { data } = await marketApi.getOverview()
    indices.value = data.indices || []
    fundFlow.value = data.fund_flow
  } catch (e) {
    console.error('加载市场概览失败', e)
  }
  await loadChart()
}

const loadChart = async () => {
  try {
    const { data } = await marketApi.getIndexDetail('000001', 30)
    await nextTick()
    if (!chartRef.value) return
    if (!chart) chart = echarts.init(chartRef.value)
    const klines = data.klines || []

    const isUp = klines.length >= 2 && klines[klines.length - 1].close >= klines[0].close

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(30, 41, 59, 0.9)',
        borderColor: 'transparent',
        textStyle: { color: '#fff' },
        formatter: (params) => {
          const d = params[0]
          return `<div style="font-weight:600">${d.axisValue}</div><div>收盘: ${d.value}</div>`
        }
      },
      grid: { left: '3%', right: '3%', bottom: '10%', top: '5%', containLabel: true },
      xAxis: {
        type: 'category',
        data: klines.map(k => k.date),
        axisLine: { lineStyle: { color: 'var(--color-border)' } },
        axisLabel: {
          color: 'var(--color-foreground-muted)',
          fontSize: 11,
          rotate: 30
        },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLine: { show: false },
        axisLabel: { color: 'var(--color-foreground-muted)', fontSize: 11 },
        splitLine: { lineStyle: { color: 'var(--color-border)', type: 'dashed' } }
      },
      dataZoom: [
        { type: 'inside', start: 50, end: 100 },
        { type: 'slider', start: 50, end: 100, height: 20, bottom: 5 }
      ],
      series: [{
        name: '收盘价',
        type: 'line',
        data: klines.map(k => k.close),
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 3,
          color: isUp ? '#DC2626' : '#16A34A'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: isUp ? 'rgba(220, 38, 38, 0.25)' : 'rgba(22, 163, 74, 0.25)' },
            { offset: 1, color: isUp ? 'rgba(220, 38, 38, 0)' : 'rgba(22, 163, 74, 0)' }
          ])
        }
      }]
    })
  } catch (e) {
    console.error('加载图表失败', e)
  }
}

const handleRefresh = async () => {
  refreshing.value = true
  try {
    await taskApi.refresh()
    setTimeout(pollStatus, 1000)
  } catch (e) {
    refreshing.value = false
    console.error(e)
  }
}

const pollStatus = async () => {
  try {
    const { data } = await taskApi.getStatus()
    taskStatus.value = data
    if (data.running) {
      setTimeout(pollStatus, 2000)
    } else {
      refreshing.value = false
      await loadData()
    }
  } catch (e) {
    refreshing.value = false
  }
}

const goIndexDetail = (code) => {
  router.push('/funds')
}

const openAiDrawer = () => {
  emit('open-ai-drawer')
}

const loadStatus = async () => {
  try {
    const { data } = await taskApi.getStatus()
    taskStatus.value = data
  } catch (e) {}
}

onMounted(async () => {
  await loadData()
  await loadStatus()
  window.addEventListener('resize', resizeChart)
})

const resizeChart = () => chart && chart.resize()

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart && chart.dispose()
})
</script>

<style scoped>
.market-overview {
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

.page-header h2 {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-foreground);
}

.actions {
  display: flex;
  gap: var(--spacing-sm);
}

.btn-icon {
  width: 16px;
  height: 16px;
  margin-right: 6px;
}

.status-alert {
  margin-bottom: var(--spacing-lg);
  border-radius: var(--radius-md);
}

.alert-icon {
  width: 18px;
  height: 18px;
}

/* === Indices Grid === */
.indices-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

@media (max-width: 1024px) {
  .indices-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .indices-grid {
    grid-template-columns: 1fr;
  }
}

/* === AI Quick Card === */
.ai-quick-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg);
  background: linear-gradient(135deg, rgba(30, 64, 175, 0.08) 0%, rgba(217, 119, 6, 0.08) 100%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  margin-bottom: var(--spacing-lg);
}

.ai-quick-card:hover {
  border-color: var(--color-accent);
  box-shadow: 0 4px 20px rgba(217, 119, 6, 0.15);
  transform: translateY(-2px);
}

.ai-quick-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.ai-quick-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-accent), #F59E0B);
  border-radius: var(--radius-lg);
  color: white;
  box-shadow: 0 2px 8px rgba(217, 119, 6, 0.3);
}

.ai-quick-icon svg {
  width: 24px;
  height: 24px;
}

.ai-quick-text h3 {
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-foreground);
}

.ai-quick-text p {
  margin: 4px 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-foreground-secondary);
}

.ai-quick-arrow {
  color: var(--color-accent);
  transition: transform 0.3s ease;
}

.ai-quick-card:hover .ai-quick-arrow {
  transform: translateX(4px);
}

.ai-quick-arrow svg {
  width: 20px;
  height: 20px;
}

.index-card {
  cursor: pointer;
  transition: all var(--transition-normal);
  border: 2px solid transparent;
}

.index-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
  border-color: var(--color-primary-light);
}

.index-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.index-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-foreground);
}

.index-date {
  font-size: var(--font-size-xs);
  color: var(--color-foreground-muted);
}

.index-body {
  margin-bottom: var(--spacing-md);
}

.index-value {
  font-family: var(--font-mono);
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  letter-spacing: -0.02em;
  margin-bottom: var(--spacing-xs);
}

.index-change {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-medium);
}

.change-icon {
  width: 18px;
  height: 18px;
}

.change-icon.up {
  color: var(--color-up);
}

.change-icon.down {
  color: var(--color-down);
}

.index-footer {
  height: 30px;
}

.mini-chart {
  height: 100%;
  opacity: 0.6;
}

.mini-chart.up {
  color: var(--color-up);
}

.mini-chart.down {
  color: var(--color-down);
}

.mini-chart svg {
  width: 100%;
  height: 100%;
}

/* === Fund Flow Card === */
.fund-flow-card {
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

.card-date {
  font-size: var(--font-size-sm);
  color: var(--color-foreground-muted);
}

.card-badge {
  font-size: var(--font-size-xs);
  padding: 4px 10px;
  background: var(--color-muted);
  border-radius: var(--radius-full);
  color: var(--color-foreground-secondary);
}

.fund-flow-grid {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2xl);
  padding: var(--spacing-lg);
}

.flow-item {
  text-align: center;
  flex: 1;
}

.flow-label {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: var(--font-size-sm);
  color: var(--color-foreground-secondary);
  margin-bottom: var(--spacing-sm);
}

.flow-icon {
  width: 16px;
  height: 16px;
}

.flow-value {
  font-family: var(--font-mono);
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-xs);
}

.flow-desc {
  font-size: var(--font-size-xs);
  color: var(--color-foreground-muted);
}

.flow-divider {
  width: 1px;
  height: 60px;
  background: var(--color-border);
}

/* === Chart Card === */
.chart-card {
  margin-bottom: var(--spacing-lg);
}

.chart-wrapper {
  background: linear-gradient(180deg, var(--color-surface) 0%, var(--color-muted) 100%);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm);
}

.chart-container {
  height: 400px;
}

/* === Colors === */
.up {
  color: var(--color-up);
}

.down {
  color: var(--color-down);
}
</style>
