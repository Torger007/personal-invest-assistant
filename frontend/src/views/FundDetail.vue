<template>
  <div class="fund-detail">
    <div class="header">
      <h2>{{ fund.name || '基金详情' }} <span class="fund-code">({{ fund.code || code }})</span></h2>
      <el-button @click="$router.push('/funds')">返回列表</el-button>
    </div>

    <!-- 摘要卡片 -->
    <el-row :gutter="16" style="margin-bottom: 20px;">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">最新净值</div>
          <div class="stat-value">{{ latestNav.unit_nav ? latestNav.unit_nav.toFixed(4) : '--' }}</div>
          <div class="stat-date">{{ latestNav.date || '--' }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">日涨跌幅</div>
          <div class="stat-value" :class="pctClass(latestNav.daily_return)">
            {{ formatPct(latestNav.daily_return) }}
          </div>
          <div class="stat-date">累计净值 {{ latestNav.acc_nav ? latestNav.acc_nav.toFixed(4) : '--' }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">近1月收益</div>
          <div class="stat-value" :class="pctClass(return1m)">{{ formatPct(return1m) }}</div>
          <div class="stat-date">相比1月前</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">近3月收益</div>
          <div class="stat-value" :class="pctClass(return3m)">{{ formatPct(return3m) }}</div>
          <div class="stat-date">相比3月前</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 基本信息 -->
    <el-card style="margin-bottom: 20px;">
      <template #header><span>基本信息</span></template>
      <el-descriptions :column="3" border v-loading="loadingFund">
        <el-descriptions-item label="基金代码">{{ fund.code || '--' }}</el-descriptions-item>
        <el-descriptions-item label="基金名称">{{ fund.name || '--' }}</el-descriptions-item>
        <el-descriptions-item label="基金类型">{{ fund.type || '--' }}</el-descriptions-item>
        <el-descriptions-item label="基金经理">{{ fund.manager || '--' }}</el-descriptions-item>
        <el-descriptions-item label="基金公司">{{ fund.company || '--' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 净值走势 -->
    <el-card style="margin-bottom: 20px;">
      <template #header><span>净值走势（近{{ navDays }}天）</span></template>
      <div ref="chartRef" style="height: 400px;"></div>
      <el-empty v-if="!navData.length && !loadingNav" description="暂无净值数据，请先采集" />
    </el-card>

    <!-- 净值明细 -->
    <el-card>
      <template #header><span>净值明细</span></template>
      <el-table :data="navData.slice().reverse()" stripe v-loading="loadingNav" max-height="400">
        <el-table-column prop="date" label="日期" width="130">
          <template #default="{ row }">{{ formatDate(row.date) }}</template>
        </el-table-column>
        <el-table-column label="单位净值" width="120">
          <template #default="{ row }">{{ row.unit_nav ? row.unit_nav.toFixed(4) : '--' }}</template>
        </el-table-column>
        <el-table-column label="累计净值" width="120">
          <template #default="{ row }">{{ row.acc_nav ? row.acc_nav.toFixed(4) : '--' }}</template>
        </el-table-column>
        <el-table-column label="日增长率" width="120">
          <template #default="{ row }">
            <span :class="pctClass(row.daily_return)">{{ formatPct(row.daily_return) }}</span>
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

const route = useRoute()
const code = route.params.code

const fund = ref({ code })
const navData = ref([])
const navDays = 90
const loadingFund = ref(false)
const loadingNav = ref(false)
const chartRef = ref(null)
let chart = null

// 最新净值
const latestNav = computed(() => {
  if (!navData.value.length) return {}
  return navData.value[navData.value.length - 1] || {}
})

// 近1月收益率
const return1m = computed(() => {
  const data = navData.value
  if (data.length < 2) return null
  const latest = data[data.length - 1]
  // 找到约22个交易日前（约1个月）
  const idx = Math.max(0, data.length - 23)
  const past = data[idx]
  if (!past.unit_nav || !latest.unit_nav) return null
  return (latest.unit_nav - past.unit_nav) / past.unit_nav * 100
})

// 近3月收益率
const return3m = computed(() => {
  const data = navData.value
  if (data.length < 2) return null
  const latest = data[data.length - 1]
  // 找到约66个交易日前（约3个月）
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

const loadChart = async () => {
  await nextTick()
  if (!chartRef.value || !navData.value.length) return
  if (!chart) chart = echarts.init(chartRef.value)

  const dates = navData.value.map(n => formatDate(n.date))
  const unitNavs = navData.value.map(n => n.unit_nav)
  const accNavs = navData.value.map(n => n.acc_nav)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['单位净值', '累计净值'] },
    grid: { left: '5%', right: '5%', bottom: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: 30 }
    },
    yAxis: { type: 'value', scale: true },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    series: [
      {
        name: '单位净值',
        type: 'line',
        data: unitNavs,
        smooth: true,
        lineStyle: { width: 2 },
        itemStyle: { color: '#409EFF' }
      },
      {
        name: '累计净值',
        type: 'line',
        data: accNavs,
        smooth: true,
        lineStyle: { width: 2 },
        itemStyle: { color: '#E6A23C' }
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
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
}

.fund-code {
  font-size: 16px;
  color: #909399;
  font-weight: normal;
}

.stat-card {
  text-align: center;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-date {
  font-size: 12px;
  color: #C0C4CC;
  margin-top: 4px;
}

.up {
  color: #f56c6c;
}

.down {
  color: #67c23a;
}
</style>
