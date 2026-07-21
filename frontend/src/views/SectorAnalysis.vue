<template>
  <div class="sector-analysis">
    <div class="page-header">
      <h2>板块走势</h2>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <div class="card-title">
                <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10 17l5-5-5-5"/>
                  <path d="M3 12h12"/>
                </svg>
                北向资金流向趋势
              </div>
              <span class="card-badge">近30日</span>
            </div>
          </template>
          <div class="chart-wrapper">
            <div ref="chartRef" class="chart-container"></div>
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

        <el-card class="sector-card" style="margin-top: 20px;">
          <template #header>
            <div class="card-header">
              <div class="card-title">
                <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 20V10M12 20V4M6 20V14"/>
                </svg>
                板块涨跌
              </div>
            </div>
          </template>
          <el-empty :description="sectorMessage" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { marketApi } from '../api'

const flows = ref([])
const sectorMessage = ref('板块数据采集功能开发中')
const chartRef = ref(null)
let chart = null

const last5DaysSum = computed(() => {
  const data = flows.value.slice(-5)
  if (!data.length) return 0
  return data.reduce((sum, f) => sum + (f.north_flow || 0), 0)
})

const last30DaysSum = computed(() => {
  const data = flows.value
  if (!data.length) return 0
  return data.reduce((sum, f) => sum + (f.north_flow || 0), 0)
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

const loadData = async () => {
  try {
    const { data } = await marketApi.getFundFlow(30)
    flows.value = data.flows || []
  } catch (e) {
    console.error(e)
  }
  try {
    const { data } = await marketApi.getSectors()
    sectorMessage.value = data.message || '板块数据采集功能开发中'
  } catch (e) {}

  await nextTick()
  drawChart()
}

const drawChart = async () => {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const list = flows.value

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(30, 41, 59, 0.9)',
      borderColor: 'transparent',
      textStyle: { color: '#fff' },
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const d = params[0]
        const val = d.value >= 0 ? `+${d.value}` : d.value
        return `<div style="font-weight:600">${d.axisValue}</div><div>北向资金: ${val} 亿</div>`
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
      name: '北向资金(亿)',
      type: 'bar',
      data: list.map(f => (f.north_flow / 1e8).toFixed(2)),
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

const resizeChart = () => chart && chart.resize()

onMounted(async () => {
  await loadData()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart && chart.dispose()
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
  margin-bottom: var(--spacing-lg);
}

.page-header h2 {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-foreground);
}

/* === Card Styles === */
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

/* === Chart Card === */
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

.sector-card {
  height: auto;
}

/* === Colors === */
.up {
  color: var(--color-up);
}

.down {
  color: var(--color-down);
}

/* === Responsive === */
@media (max-width: 1024px) {
  .el-col-16,
  .el-col-8 {
    width: 100%;
    max-width: 100%;
    flex: 0 0 100%;
  }

  .chart-card,
  .summary-card,
  .sector-card {
    margin-bottom: var(--spacing-md);
  }
}
</style>