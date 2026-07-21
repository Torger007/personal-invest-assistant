<template>
  <div class="fund-detail">
    <div class="page-header">
      <div class="header-left">
        <el-button text @click="$router.push('/funds')" class="back-btn">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          返回列表
        </el-button>
        <div class="fund-title">
          <h2>{{ fund.name || '基金详情' }}</h2>
          <span class="fund-code">{{ fund.code || code }}</span>
        </div>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="refreshData" :loading="refreshing" class="refresh-btn">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          {{ refreshing ? '刷新中...' : '刷新数据' }}
        </el-button>
      </div>
    </div>

    <!-- 数据状态提示 -->
    <el-alert
      v-if="navData.length < navDays"
      :title="'当前数据不足' + navDays + '天，共' + navData.length + '条记录，点击「刷新数据」补充历史数据'"
      type="info"
      show-icon
      class="data-alert"
      :closable="false"
    />

    <!-- 摘要卡片 -->
    <div class="summary-grid">
      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon nav">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-label">最新净值</div>
          <div class="stat-value">{{ latestNav.unit_nav ? latestNav.unit_nav.toFixed(4) : '--' }}</div>
          <div class="stat-date">{{ latestNav.date || '--' }}</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon" :class="pctClass(latestNav.daily_return)">
          <svg v-if="latestNav.daily_return >= 0" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 4l8 8h-6v8h-4v-8H4l8-8z"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 20l-8-8h6V4h4v8h6l-8 8z"/>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-label">日涨跌幅</div>
          <div class="stat-value" :class="pctClass(latestNav.daily_return)">
            {{ formatPct(latestNav.daily_return) }}
          </div>
          <div class="stat-date">累计 {{ latestNav.acc_nav ? latestNav.acc_nav.toFixed(4) : '--' }}</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon neutral">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 3v18h18"/>
            <path d="M7 14l4-4 4 4 5-6"/>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-label">近1月收益</div>
          <div class="stat-value" :class="pctClass(return1m)">{{ formatPct(return1m) }}</div>
          <div class="stat-date">相比1月前</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="stat-card">
        <div class="stat-icon neutral">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 3v18h18"/>
            <path d="M7 16l4-6 4 4 5-8"/>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-label">近3月收益</div>
          <div class="stat-value" :class="pctClass(return3m)">{{ formatPct(return3m) }}</div>
          <div class="stat-date">相比3月前</div>
        </div>
      </el-card>
    </div>

    <!-- 基本信息 -->
    <el-card class="info-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/>
              <rect x="9" y="3" width="6" height="4" rx="1"/>
              <path d="M9 12h6M9 16h6"/>
            </svg>
            基本信息
          </div>
        </div>
      </template>
      <el-descriptions :column="3" border v-loading="loadingFund" class="info-table">
        <el-descriptions-item label="基金代码">
          <span class="mono">{{ fund.code || '--' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="基金名称">{{ fund.name || '--' }}</el-descriptions-item>
        <el-descriptions-item label="基金类型">
          <el-tag size="small">{{ fund.type || '--' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="基金经理">{{ fund.manager || '--' }}</el-descriptions-item>
        <el-descriptions-item label="基金公司">{{ fund.company || '--' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 净值走势 -->
    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 3v18h18"/>
              <path d="M7 12l4-4 4 4 5-6"/>
            </svg>
            净值走势
          </div>
          <span class="card-badge">近{{ navDays }}天</span>
        </div>
      </template>
      <div class="chart-wrapper">
        <div ref="chartRef" class="chart-container"></div>
      </div>
      <el-empty v-if="!navData.length && !loadingNav" description="暂无净值数据，请先采集" />
    </el-card>

    <!-- 净值明细 -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 3h18v18H3z"/>
              <path d="M3 9h18M3 15h18M9 3v18"/>
            </svg>
            净值明细
          </div>
          <div class="table-actions">
            <el-tag v-if="navData.length > 0" type="info" size="small">共 {{ navData.length }} 条</el-tag>
          </div>
        </div>
      </template>
      <el-table :data="navData.slice().reverse()" stripe v-loading="loadingNav" max-height="400" class="nav-table">
        <el-table-column prop="date" label="日期" width="130">
          <template #default="{ row }">
            <span class="mono">{{ formatDate(row.date) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="单位净值" width="120">
          <template #default="{ row }">
            <span class="mono">{{ row.unit_nav ? row.unit_nav.toFixed(4) : '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="累计净值" width="120">
          <template #default="{ row }">
            <span class="mono">{{ row.acc_nav ? row.acc_nav.toFixed(4) : '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="日增长率" width="120">
          <template #default="{ row }">
            <span class="mono" :class="pctClass(row.daily_return)">{{ formatPct(row.daily_return) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { fundApi } from '../api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const code = route.params.code

const fund = ref({ code })
const navData = ref([])
const navDays = 90
const loadingFund = ref(false)
const loadingNav = ref(false)
const refreshing = ref(false)
const chartRef = ref(null)
let chart = null

const latestNav = computed(() => {
  if (!navData.value.length) return {}
  return navData.value[navData.value.length - 1] || {}
})

const return1m = computed(() => {
  const data = navData.value
  if (data.length < 2) return null
  const latest = data[data.length - 1]
  const idx = Math.max(0, data.length - 23)
  const past = data[idx]
  if (!past.unit_nav || !latest.unit_nav) return null
  return (latest.unit_nav - past.unit_nav) / past.unit_nav * 100
})

const return3m = computed(() => {
  const data = navData.value
  if (data.length < 2) return null
  const latest = data[data.length - 1]
  const idx = Math.max(0, data.length - 67)
  const past = data[idx]
  if (!past.unit_nav || !latest.unit_nav) return null
  return (latest.unit_nav - past.unit_nav) / past.unit_nav * 100
})

const pctClass = (val) => {
  if (val === null || val === undefined) return ''
  return val > 0 ? 'up' : val < 0 ? 'down' : ''
}

const formatPct = (val) => {
  if (val === null || val === undefined) return '--'
  const sign = val >= 0 ? '+' : ''
  return `${sign}${val.toFixed(2)}%`
}

const formatDate = (val) => {
  if (!val) return '--'
  const d = typeof val === 'string' ? val : String(val)
  return d.substring(0, 10)
}

const loadFund = async () => {
  loadingFund.value = true
  try {
    const { data } = await fundApi.getDetail(code)
    if (!data.error) fund.value = data
  } catch (e) {
    console.error('加载基金信息失败', e)
  } finally {
    loadingFund.value = false
  }
}

const loadNav = async () => {
  loadingNav.value = true
  try {
    const { data } = await fundApi.getNav(code, navDays)
    navData.value = data.nav || []
  } catch (e) {
    console.error('加载净值数据失败', e)
  } finally {
    loadingNav.value = false
  }
}

const refreshData = async () => {
  refreshing.value = true
  try {
    const { data } = await fundApi.refresh(code, navDays)
    if (data.errors && data.errors.length > 0) {
      ElMessage.warning(`刷新完成，但有错误: ${data.errors.join(', ')}`)
    } else {
      ElMessage.success(`数据刷新成功！共 ${data.nav_count} 条记录`)
    }
    // 刷新完成后重新加载数据
    await loadNav()
    await loadChart()
  } catch (e) {
    console.error('刷新数据失败', e)
    ElMessage.error('刷新数据失败')
  } finally {
    refreshing.value = false
  }
}

const loadChart = async () => {
  await nextTick()
  if (!chartRef.value || !navData.value.length) return
  if (!chart) chart = echarts.init(chartRef.value)

  const dates = navData.value.map(n => formatDate(n.date))
  const unitNavs = navData.value.map(n => n.unit_nav)
  const accNavs = navData.value.map(n => n.acc_nav)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(30, 41, 59, 0.9)',
      borderColor: 'transparent',
      textStyle: { color: '#fff' },
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['单位净值', '累计净值'],
      top: 10,
      textStyle: { color: 'var(--color-foreground-secondary)' }
    },
    grid: { left: '3%', right: '3%', bottom: '12%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
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
    series: [
      {
        name: '单位净值',
        type: 'line',
        data: unitNavs,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 3, color: '#1E40AF' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(30, 64, 175, 0.2)' },
            { offset: 1, color: 'rgba(30, 64, 175, 0)' }
          ])
        }
      },
      {
        name: '累计净值',
        type: 'line',
        data: accNavs,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 3, color: '#D97706' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(217, 119, 6, 0.15)' },
            { offset: 1, color: 'rgba(217, 119, 6, 0)' }
          ])
        }
      }
    ]
  })
}

const resizeChart = () => chart && chart.resize()

onMounted(async () => {
  await loadFund()
  await loadNav()
  await loadChart()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart && chart.dispose()
})
</script>

<style scoped>
.fund-detail {
  padding: var(--spacing-lg);
  max-width: 1400px;
  margin: 0 auto;
}

/* === Page Header === */
.page-header {
  margin-bottom: var(--spacing-lg);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-right {
  display: flex;
  gap: var(--spacing-sm);
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
}

.data-alert {
  margin-bottom: var(--spacing-md);
}

.table-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
}

.back-btn {
  padding: 8px 12px;
  color: var(--color-foreground-secondary);
}

.btn-icon {
  width: 18px;
  height: 18px;
  margin-right: 4px;
}

.fund-title {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-sm);
}

.fund-title h2 {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-foreground);
}

.fund-code {
  font-size: var(--font-size-base);
  color: var(--color-foreground-muted);
  font-family: var(--font-mono);
}

/* === Summary Grid === */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

@media (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  transition: all var(--transition-normal);
  border: 2px solid transparent;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
  border-color: var(--color-border);
}

.stat-icon {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--color-muted);
}

.stat-icon svg {
  width: 24px;
  height: 24px;
}

.stat-icon.nav {
  background: rgba(30, 64, 175, 0.1);
  color: var(--color-primary);
}

.stat-icon.up {
  background: rgba(220, 38, 38, 0.1);
  color: var(--color-up);
}

.stat-icon.down {
  background: rgba(22, 163, 74, 0.1);
  color: var(--color-down);
}

.stat-icon.neutral {
  background: var(--color-muted);
  color: var(--color-foreground-secondary);
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-foreground-secondary);
  margin-bottom: var(--spacing-xs);
}

.stat-value {
  font-family: var(--font-mono);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-foreground);
  letter-spacing: -0.02em;
}

.stat-date {
  font-size: var(--font-size-xs);
  color: var(--color-foreground-muted);
  margin-top: var(--spacing-xs);
}

/* === Info Card === */
.info-card {
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

.info-table .mono {
  font-family: var(--font-mono);
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

/* === Table Card === */
.table-card {
  margin-bottom: var(--spacing-lg);
}

.nav-table .mono {
  font-family: var(--font-mono);
}

/* === Colors === */
.up {
  color: var(--color-up);
}

.down {
  color: var(--color-down);
}
</style>