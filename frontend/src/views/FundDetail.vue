<template>
  <div class="fund-detail">
    <div class="header">
      <h2>基金详情</h2>
      <el-button @click="$router.push('/funds')">返回列表</el-button>
    </div>

    <el-card v-loading="loading">
      <template #header>
        <span>{{ fund.name || '加载中...' }} ({{ fund.code }})</span>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="基金代码">{{ fund.code }}</el-descriptions-item>
        <el-descriptions-item label="基金名称">{{ fund.name || '--' }}</el-descriptions-item>
        <el-descriptions-item label="基金类型">{{ fund.type || '--' }}</el-descriptions-item>
        <el-descriptions-item label="基金经理">{{ fund.manager || '--' }}</el-descriptions-item>
        <el-descriptions-item label="基金公司">{{ fund.company || '--' }}</el-descriptions-item>
        <el-descriptions-item label="成立日期">{{ fund.create_date || '--' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card style="margin-top: 20px;">
      <template #header>
        <span>净值走势</span>
      </template>
      <div ref="chartRef" style="height: 400px;"></div>
      <el-empty v-if="!navData.length" description="暂无净值数据（需要先采集该基金净值）" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { fundApi } from '../api'

const route = useRoute()
const fund = ref({ code: route.params.code })
const navData = ref([])
const loading = ref(false)
const chartRef = ref(null)
let chart = null

const loadFund = async () => {
  loading.value = true
  try {
    const { data } = await fundApi.getDetail(route.params.code)
    if (!data.error) fund.value = data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const loadChart = async () => {
  await nextTick()
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['单位净值'] },
    grid: { left: '5%', right: '5%', bottom: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: navData.value.map(n => n.date),
      axisLabel: { rotate: 30 }
    },
    yAxis: { type: 'value', scale: true },
    series: [{
      name: '单位净值',
      type: 'line',
      data: navData.value.map(n => n.unit_nav),
      smooth: true
    }]
  })
}

const resizeChart = () => chart && chart.resize()

onMounted(async () => {
  await loadFund()
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
</style>