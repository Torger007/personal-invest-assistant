<template>
  <div class="advice-report">
    <h2>投资建议</h2>
    <el-alert
      title="本系统仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
      type="warning"
      :closable="false"
      style="margin-bottom: 16px;"
    />

    <el-card v-loading="loading">
      <template #header>
        <span>最新建议列表</span>
      </template>
      <el-table :data="adviceList" stripe>
        <el-table-column prop="fund_code" label="基金代码" width="120" />
        <el-table-column prop="date" label="日期" width="150" />
        <el-table-column prop="overall_signal" label="操作建议" width="140" />
        <el-table-column label="置信度" width="120">
          <template #default="{ row }">
            <span>{{ row.confidence ? row.confidence + '%' : '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row.fund_code)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && adviceList.length === 0" description="暂无建议记录，请先采集数据并生成建议" />
    </el-card>

    <!-- 建议详情对话框 -->
    <el-dialog v-model="detailVisible" title="建议详情" width="700px">
      <div v-if="detail" class="advice-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="基金代码">{{ detail.fund_code }}</el-descriptions-item>
          <el-descriptions-item label="日期">{{ detail.date }}</el-descriptions-item>
          <el-descriptions-item label="操作建议">
            <el-tag :type="signalTagType(detail.overall_signal)">{{ detail.overall_signal }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">{{ detail.confidence }}%</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin-top: 16px;">各维度评分</h4>
        <el-row :gutter="10">
          <el-col :span="6">
            <el-statistic title="技术面" :value="detail.scores?.technical ?? '--'" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="估值面" :value="detail.scores?.valuation ?? '--'" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="资金面" :value="detail.scores?.fund_flow ?? '--'" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="情绪面" :value="detail.scores?.sentiment ?? '--'" />
          </el-col>
        </el-row>

        <pre class="advice-text">{{ detail.advice_text?.advice_text || detail.advice_text || '暂无详细分析' }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adviceApi } from '../api'

const adviceList = ref([])
const loading = ref(false)
const detailVisible = ref(false)
const detail = ref(null)

const loadList = async () => {
  loading.value = true
  try {
    const { data } = await adviceApi.getList()
    adviceList.value = data.advice || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const viewDetail = async (code) => {
  try {
    const { data } = await adviceApi.getFundAdvice(code)
    detail.value = data
    detailVisible.value = true
  } catch (e) {
    console.error(e)
  }
}

const signalTagType = (signal) => {
  if (!signal) return 'info'
  if (signal.includes('加仓')) return 'success'
  if (signal.includes('止盈') || signal.includes('减仓')) return 'danger'
  return 'warning'
}

onMounted(loadList)
</script>

<style scoped>
.advice-report {
  padding: 20px;
}

.advice-text {
  margin-top: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
}
</style>