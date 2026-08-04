<template>
  <div class="sector-analysis">
    <div class="page-header">
      <h2>板块走势</h2>
      <div class="actions">
        <el-button type="primary" :loading="refreshing" @click="handleRefresh">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 0 1-9 9m9-9a9 9 0 0 0-9-9m9 9H3m9 9a9 9 0 0 1-9-9m9 9c1.66 0 3-4.03 3-9s-1.34-9-3-9m0 18c-1.66 0-3-4.03-3-9s1.34-9 3-9m-9 9a9 9 0 0 1 9-9"/>
          </svg>
          采集数据
        </el-button>
      </div>
    </div>

    <!-- 资金流向趋势 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <div class="card-title">
                <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10 17l5-5-5-5"/>
                  <path d="M3 12h12"/>
                </svg>
                主力资金流向趋势
              </div>
              <span class="card-badge">近30日</span>
            </div>
          </template>
          <div class="chart-wrapper">
            <div ref="flowChartRef" class="chart-container"></div>
          </div>
          <el-empty v-if="!flows.length" description="暂无资金流向数据，请先采集" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="summary-card">
          <template #header>
            <div class="card-header">
              <div class="card-title">
                <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                </svg>
                资金概览
              </div>
            </div>
          </template>
          <div class="summary-stats">
            <div class="summary-item">
              <div class="summary-label">近5日净流入</div>
              <div class="summary-value" :class="flowClass(last5DaysSum)">
                {{ formatFlow(last5DaysSum) }}
              </div>
            </div>
            <el-divider />
            <div class="summary-item">
              <div class="summary-label">近30日净流入</div>
              <div class="summary-value" :class="flowClass(last30DaysSum)">
                {{ formatFlow(last30DaysSum) }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 板块涨跌排行 -->
    <el-card class="sector-rank-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 20V10M12 20V4M6 20V14"/>
            </svg>
            板块涨跌排行
          </div>
          <div class="header-right">
            <el-radio-group v-model="sectorType" size="small" @change="loadSectors">
              <el-radio-button value="concept">概念板块</el-radio-button>
              <el-radio-button value="industry">行业板块</el-radio-button>
            </el-radio-group>
            <span class="card-badge" style="margin-left: 12px;" v-if="updateTime">
              更新于 {{ updateTime }}
            </span>
          </div>
        </div>
      </template>

      <div v-if="sectors.length" class="sector-grid">
        <!-- 涨幅榜 -->
        <div class="sector-column">
          <div class="column-title up">
            <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
              <path d="M12 4l8 8h-6v8h-4v-8H4l8-8z"/>
            </svg>
            涨幅榜 Top10
          </div>
          <div
            v-for="(s, idx) in topGainers"
            :key="s.name"
            class="sector-item gainer"
            :class="{ active: selectedSector === s.name }"
            @click="selectSector(s.name)"
          >
            <span class="rank-num" :class="idx < 3 ? 'top' + (idx + 1) : ''">{{ idx + 1 }}</span>
            <div class="sector-info">
              <span class="sector-name">{{ s.name }}</span>
              <span class="sector-leader" v-if="s.leader">领涨: {{ s.leader }}</span>
            </div>
            <span class="sector-change up">{{ formatPct(s.change_pct) }}</span>
          </div>
        </div>

        <!-- 跌幅榜 -->
        <div class="sector-column">
          <div class="column-title down">
            <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
              <path d="M12 20l-8-8h6V4h4v8h6l-8 8z"/>
            </svg>
            跌幅榜 Top10
          </div>
          <div
            v-for="(s, idx) in topLosers"
            :key="s.name"
            class="sector-item loser"
            :class="{ active: selectedSector === s.name }"
            @click="selectSector(s.name)"
          >
            <span class="rank-num" :class="idx < 3 ? 'top' + (idx + 1) : ''">{{ idx + 1 }}</span>
            <div class="sector-info">
              <span class="sector-name">{{ s.name }}</span>
              <span class="sector-leader" v-if="s.leader">领跌: {{ s.leader }}</span>
            </div>
            <span class="sector-change down">{{ formatPct(s.change_pct) }}</span>
          </div>
        </div>
      </div>

      <el-empty v-else :description="sectorMessage" :image-size="80" />

      <!-- 板块K线图 -->
      <div v-if="selectedSector" class="sector-chart-section">
        <el-divider />
        <div class="sector-chart-header">
          <div class="card-title">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 3v18h18"/>
              <path d="M7 12l4-4 4 4 5-6"/>
            </svg>
            {{ selectedSector }} 走势图
          </div>
          <span class="card-badge">近{{ histDays }}日</span>
        </div>
        <div class="chart-wrapper" style="margin-top: 12px;">
          <div ref="sectorChartRef" class="chart-container"></div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { marketApi, taskApi } from '../api'

// ============== 资金流向 ==============
const flows = ref([])
const flowChartRef = ref(null)
let flowChart = null

const last5DaysSum = computed(() => {
  const data = flows.value.slice(-5)
  if (!data.length) return 0
  return data.reduce((sum, f) => sum + (f.main_flow || 0), 0)
})

const last30DaysSum = computed(() => {
  const data = flows.value
  if (!data.length) return 0
  return data.reduce((sum, f) => sum + (f.main_flow || 0), 0)
})

const flowClass = (val) => {
  if (val === null || val === undefined) return ''
  return val > 0 ? 'up' : val < 0 ? 'down' : ''
}

const formatFlow = (val) => {
  if (val === null || val === undefined || isNaN(val)) return '--'
  const yi = val / 1e8
  const sign = val >= 0 ? '+' : ''
  return `${sign}${yi.toFixed(2)} 亿`
}

const formatPct = (val) => {
  if (val === null || val === undefined) return '--'
  const sign = val >= 0 ? '+' : ''
  return `${sign}${val.toFixed(2)}%`
}

// ============== 板块数据 ==============
const sectorType = ref('concept')
const sectors = ref([])
const sectorMessage = ref('加载中...')
const updateTime = ref(null)
const refreshing = ref(false)
const selectedSector = ref(null)
const sectorHist = ref([])
const histDays = ref(30)
const sectorChartRef = ref(null)
let sectorChart = null

const topGainers = computed(() => {
  const list = [...sectors.value].sort((a, b) => (b.change_pct || 0) - (a.change_pct || 0))
  return list.slice(0, 10)
})

const topLosers = computed(() => {
  // 首先尝试找真实下跌的板块
  const losers = [...sectors.value].filter(s => (s.change_pct || 0) < 0).sort((a, b) => (a.change_pct || 0) - (b.change_pct || 0))
  if (losers.length > 0) {
    return losers.slice(0, 10)
  }
  // 如果没有下跌的，就显示涨幅最小的板块
  const all = [...sectors.value].filter(s => (s.change_pct || 0) !== 0).sort((a, b) => (a.change_pct || 0) - (b.change_pct || 0))
  return all.slice(0, 10)
})

// ============== 数据加载 ==============
const loadData = async () => {
  await Promise.all([loadFlows(), loadSectors()])
}

const loadFlows = async () => {
  try {
    const { data } = await marketApi.getFundFlow(30)
    flows.value = data.flows || []
  } catch (e) {
    console.error('加载资金流向失败', e)
  }
  await nextTick()
  drawFlowChart()
}

const loadSectors = async () => {
  try {
    const { data } = await marketApi.getSectors(sectorType.value, 50)
    sectors.value = data.sectors || []
    sectorMessage.value = data.message || '暂无数据，请先采集'
    updateTime.value = data.update_time || null
  } catch (e) {
    console.error('加载板块数据失败', e)
    sectorMessage.value = '加载失败'
  }
}

const selectSector = async (name) => {
  if (selectedSector.value === name) {
    selectedSector.value = null
    return
  }
  selectedSector.value = name

  try {
    const { data } = await marketApi.getSectorHist(name, histDays.value)
    sectorHist.value = data.klines || []
  } catch (e) {
    console.error('加载板块历史失败', e)
  }
  await nextTick()
  drawSectorChart()
}

const handleRefresh = async () => {
  refreshing.value = true
  try {
    const { data: started } = await taskApi.refresh()
    if (started.status === 'skipped') {
      ElMessage.warning(started.message || '已有更新任务正在运行')
    }
    let attempts = 0
    const poll = async () => {
      if (attempts++ > 60) {
        refreshing.value = false
        ElMessage.warning('数据更新仍在执行，请稍后刷新页面查看结果')
        return
      }
      try {
        const { data } = await taskApi.getStatus()
        if (data.running) {
          setTimeout(poll, 2000)
        } else {
          refreshing.value = false
          const result = data.last_result
          if (!result) {
            ElMessage.warning('未获取到本次更新结果，请稍后重试')
            return
          }
          if (result.status === 'failed') {
            ElMessage.error(result.error || '数据更新失败')
            return
          }
          await loadData()
          if (result.status === 'partial') {
            const failedStages = Object.entries(result.stages || {})
              .filter(([, stage]) => stage.status !== 'success')
              .map(([name]) => name)
            ElMessage.warning(`数据已部分更新${failedStages.length ? `：${failedStages.join('、')}` : ''}`)
          } else {
            ElMessage.success('数据已更新')
          }
        }
      } catch (error) {
        refreshing.value = false
        ElMessage.error('无法获取更新状态')
        console.error(error)
      }
    }
    setTimeout(poll, 1000)
  } catch (e) {
    refreshing.value = false
    ElMessage.error('无法启动数据更新')
    console.error(e)
  }
}

// ============== 图表绘制 ==============
const drawFlowChart = () => {
  if (!flowChartRef.value) return
  if (!flowChart) flowChart = echarts.init(flowChartRef.value)
  const list = flows.value

  flowChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(30, 41, 59, 0.9)',
      borderColor: 'transparent',
      textStyle: { color: '#fff' },
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const d = params[0]
        const val = d.value >= 0 ? `+${d.value}` : d.value
        return `<div style="font-weight:600">${d.axisValue}</div><div>主力资金: ${val} 亿</div>`
      }
    },
    grid: { left: '3%', right: '3%', bottom: '12%', top: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: list.map(f => f.date),
      axisLine: { lineStyle: { color: 'var(--color-border)' } },
      axisLabel: { color: 'var(--color-foreground-muted)', fontSize: 11, rotate: 30 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      name: '亿元',
      nameTextStyle: { color: 'var(--color-foreground-muted)' },
      axisLine: { show: false },
      axisLabel: { color: 'var(--color-foreground-muted)', fontSize: 11 },
      splitLine: { lineStyle: { color: 'var(--color-border)', type: 'dashed' } }
    },
    dataZoom: [
      { type: 'inside', start: 50, end: 100 },
      { type: 'slider', start: 50, end: 100, height: 20, bottom: 5 }
    ],
    series: [{
      name: '主力资金(亿)',
      type: 'bar',
      data: list.map(f => (f.main_flow / 1e8).toFixed(2)),
      barWidth: '60%',
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: (params) => {
          return params.value >= 0
            ? new echarts.graphic.LinearGradient(0, 1, 0, 0, [
                { offset: 0, color: 'rgba(220, 38, 38, 0.6)' },
                { offset: 1, color: '#DC2626' }
              ])
            : new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(22, 163, 74, 0.6)' },
                { offset: 1, color: '#16A34A' }
              ])
        }
      }
    }]
  })
}

const drawSectorChart = () => {
  if (!sectorChartRef.value) return
  if (!sectorChart) sectorChart = echarts.init(sectorChartRef.value)
  const klines = sectorHist.value
  if (!klines.length) return

  const isUp = klines.length >= 2 && klines[klines.length - 1].close >= klines[0].close

  sectorChart.setOption({
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
      axisLabel: { color: 'var(--color-foreground-muted)', fontSize: 11, rotate: 30 },
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
}

// ============== resize ==============
const resizeAllCharts = () => {
  flowChart?.resize()
  sectorChart?.resize()
}

// ============== 生命周期 ==============
onMounted(async () => {
  await loadData()
  window.addEventListener('resize', resizeAllCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeAllCharts)
  flowChart?.dispose()
  sectorChart?.dispose()
})

// 当选中板块变化时，重新绘制K线图
watch(sectorHist, async () => {
  await nextTick()
  drawSectorChart()
})
</script>

<style scoped>
.sector-analysis {
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

/* === Card Styles === */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-right {
  display: flex;
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

/* === Chart === */
.chart-card {
  height: 100%;
}

.chart-wrapper {
  background: linear-gradient(180deg, var(--color-surface) 0%, var(--color-muted) 100%);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm);
}

.chart-container {
  height: 400px;
}

/* === Summary Card === */
.summary-card {
  height: auto;
}

.summary-stats {
  padding: var(--spacing-sm);
}

.summary-item {
  text-align: center;
}

.summary-label {
  font-size: var(--font-size-sm);
  color: var(--color-foreground-secondary);
  margin-bottom: var(--spacing-sm);
}

.summary-value {
  font-family: var(--font-mono);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
}

/* === Sector Rank === */
.sector-rank-card {
  margin-top: 0;
}

.sector-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
}

@media (max-width: 768px) {
  .sector-grid {
    grid-template-columns: 1fr;
  }
}

.sector-column {
  background: var(--color-muted);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
}

.column-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-sm);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-border);
}

.column-title.up { color: var(--color-up); }
.column-title.down { color: var(--color-down); }

.sector-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.sector-item:hover {
  background: var(--color-surface);
}

.sector-item.active {
  background: var(--color-primary-light);
  box-shadow: inset 0 0 0 1px var(--color-primary);
}

.rank-num {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-foreground-secondary);
  flex-shrink: 0;
}

.rank-num.top1 { background: #FFD700; color: #000; }
.rank-num.top2 { background: #C0C0C0; color: #000; }
.rank-num.top3 { background: #CD7F32; color: #fff; }

.sector-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.sector-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-foreground);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sector-leader {
  font-size: var(--font-size-xs);
  color: var(--color-foreground-muted);
  margin-top: 2px;
}

.sector-change {
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  flex-shrink: 0;
}

/* === Sector Chart Section === */
.sector-chart-section {
  margin-top: var(--spacing-md);
}

.sector-chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* === Colors === */
.up { color: var(--color-up); }
.down { color: var(--color-down); }

/* === Responsive === */
@media (max-width: 1024px) {
  .el-col-16,
  .el-col-8 {
    width: 100%;
    max-width: 100%;
    flex: 0 0 100%;
  }

  .chart-card,
  .summary-card {
    margin-bottom: var(--spacing-md);
  }
}
</style>
