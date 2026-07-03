<template>
  <div class="market-overview">
    <div class="header">
      <h2>市场概览</h2>
      <div class="actions">
        <el-button type="primary" :loading="refreshing" @click="handleRefresh">
          手动采集数据
        </el-button>
        <el-button @click="loadData">刷新</el-button>
      </div>
    </div>

    <!-- 任务状态提示 -->
    <el-alert
      v-if="taskStatus"
      :title="taskStatusMessage"
      type="info"
      :closable="false"
      style="margin-bottom: 16px;"
    />

    <!-- 指数卡片 -->
    <el-row :gutter="20">
      <el-col :span="8" v-for="item in indices" :key="item.code">
        <el-card shadow="hover" @click="goIndexDetail(item.code)">
          <template #header>
            <div class="card-header">
              <span>{{ item.name }}</span>
              <span class="card-date">{{ item.date || '--' }}</span>
            </div>
          </template>
          <div class="index-value" :class="changeClass(item.change_pct)">
            {{ item.value ? item.value.toFixed(2) : '--' }}
          </div>
          <div class="index-change" :class="changeClass(item.change_pct)">
            {{ formatChange(item.change, item.change_pct) }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 资金流向 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>资金流向（最新）</span>
      </template>
      <el-descriptions :column="3" border v-if="fundFlow">
        <el-descriptions-item label="日期">{{ fundFlow.date || '--' }}</el-descriptions-item>
        <el-descriptions-item label="北向资金">
          <span :class="flowClass(fundFlow.north_flow)">
            {{ formatFlow(fundFlow.north_flow) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="主力资金">
          <span :class="flowClass(fundFlow.main_flow)">
            {{ formatFlow(fundFlow.main_flow) }}
          </span>
        </el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="暂无资金流向数据，请先采集" />
    </el-card>

    <!-- 上证指数走势图 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>上证指数近30日走势</span>
      </template>
      <div ref="chartRef" style="height: 400px;"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { marketApi, taskApi } from '../api'

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
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['收盘价'] },
      grid: { left: '5%', right: '5%', bottom: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        data: klines.map(k => k.date),
        axisLabel: { rotate: 30 }
      },
      yAxis: { type: 'value', scale: true },
      dataZoom: [{ type: 'inside' }, { type: 'slider' }],
      series: [{
        name: '收盘价',
        type: 'line',
        data: klines.map(k => k.close),
        smooth: true,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.1 }
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
    // 轮询任务状态
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
      await loadData()  // 采集完重新加载数据
    }
  } catch (e) {
    refreshing.value = false
  }
}

const goIndexDetail = (code) => {
  router.push(`/funds/${code}`)
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-date {
  font-size: 12px;
  color: #909399;
}

.index-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.index-change {
  font-size: 14px;
  margin-top: 8px;
}

.up {
  color: #f56c6c;
}

.down {
  color: #67c23a;
}
</style>