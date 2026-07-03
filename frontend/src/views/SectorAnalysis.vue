<template>
  <div class="sector-analysis">
    <h2>板块走势</h2>
    <el-card>
      <template #header>
        <span>资金流向趋势（北向资金）</span>
      </template>
      <div ref="chartRef" style="height: 400px;"></div>
      <el-empty v-if="!flows.length" description="暂无资金流向数据，请先采集" />
    </el-card>

    <el-card style="margin-top: 20px;">
      <template #header>
        <span>板块涨跌</span>
      </template>
      <el-empty :description="sectorMessage" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { marketApi } from '../api'

const flows = ref([])
const sectorMessage = ref('板块数据采集功能开发中')
const chartRef = ref(null)
let chart = null

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
    tooltip: { trigger: 'axis' },
    legend: { data: ['北向资金(亿)'] },
    grid: { left: '5%', right: '5%', bottom: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: list.map(f => f.date),
      axisLabel: { rotate: 30 }
    },
    yAxis: { type: 'value', name: '亿元' },
    series: [{
      name: '北向资金(亿)',
      type: 'bar',
      data: list.map(f => (f.north_flow / 1e8).toFixed(2)),
      itemStyle: {
        color: (params) => params.value >= 0 ? '#f56c6c' : '#67c23a'
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
  padding: 20px;
}
</style>