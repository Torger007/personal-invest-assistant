<template>
  <div class="advice-report">
    <div class="page-header">
      <h2>投资建议</h2>
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

    <el-card class="table-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <svg class="card-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/>
              <rect x="9" y="3" width="6" height="4" rx="1"/>
              <path d="M9 14l2 2 4-4"/>
            </svg>
            最新建议列表
          </div>
        </div>
      </template>

      <el-table :data="adviceList" stripe class="advice-table">
        <el-table-column prop="fund_code" label="基金代码" width="120">
          <template #default="{ row }">
            <span class="mono code">{{ row.fund_code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="date" label="日期" width="150">
          <template #default="{ row }">
            <span class="mono">{{ row.date }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="overall_signal" label="操作建议" width="160">
          <template #default="{ row }">
            <el-tag :type="signalTagType(row.overall_signal)" size="small" class="signal-tag">
              {{ row.overall_signal || '--' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="140">
          <template #default="{ row }">
            <div class="confidence-cell">
              <div class="confidence-bar">
                <div
                  class="confidence-fill"
                  :style="{ width: `${row.confidence || 0}%` }"
                ></div>
              </div>
              <span class="confidence-value mono">{{ row.confidence ? row.confidence + '%' : '--' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row.fund_code)" class="detail-btn">
              <svg class="btn-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && adviceList.length === 0" description="暂无建议记录，请先采集数据并生成建议" />
    </el-card>

    <!-- 建议详情对话框 -->
    <el-dialog v-model="detailVisible" title="建议详情" width="760px" class="detail-dialog">
      <div v-if="detail" class="advice-detail">
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

        <div class="scores-section">
          <h4 class="section-title">
            <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 3v18h18"/>
              <path d="M7 14l4-4 4 4 5-6"/>
            </svg>
            各维度评分
          </h4>
          <div class="scores-grid">
            <div class="score-card">
              <div class="score-label">技术面</div>
              <div class="score-value">{{ detail.scores?.technical ?? '--' }}</div>
            </div>
            <div class="score-card">
              <div class="score-label">估值面</div>
              <div class="score-value">{{ detail.scores?.valuation ?? '--' }}</div>
            </div>
            <div class="score-card">
              <div class="score-label">资金面</div>
              <div class="score-value">{{ detail.scores?.fund_flow ?? '--' }}</div>
            </div>
            <div class="score-card">
              <div class="score-label">情绪面</div>
              <div class="score-value">{{ detail.scores?.sentiment ?? '--' }}</div>
            </div>
          </div>
        </div>

        <div class="analysis-section">
          <h4 class="section-title">
            <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>
            </svg>
            分析详情
          </h4>
          <div class="analysis-content">
            {{ detail.advice_text?.advice_text || detail.advice_text || '暂无详细分析' }}
          </div>
        </div>
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

/* === Warning Alert === */
.warning-alert {
  margin-bottom: var(--spacing-lg);
  border-radius: var(--radius-md);
}

.alert-icon {
  width: 20px;
  height: 20px;
}

/* === Table Card === */
.table-card {
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

.advice-table .code {
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
}

.signal-tag {
  border-radius: var(--radius-full);
}

.confidence-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.confidence-bar {
  flex: 1;
  height: 6px;
  background: var(--color-muted);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  border-radius: var(--radius-full);
  transition: width var(--transition-normal);
}

.confidence-value {
  flex-shrink: 0;
  font-size: var(--font-size-sm);
  color: var(--color-foreground-secondary);
}

.detail-btn {
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-icon-sm {
  width: 14px;
  height: 14px;
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

/* === Scores Section === */
.scores-section {
  margin-bottom: var(--spacing-lg);
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

.section-icon {
  width: 18px;
  height: 18px;
  color: var(--color-primary);
}

.scores-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
}

.score-card {
  text-align: center;
  padding: var(--spacing-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.score-card:hover {
  border-color: var(--color-primary-light);
  box-shadow: var(--shadow-sm);
}

.score-label {
  font-size: var(--font-size-sm);
  color: var(--color-foreground-secondary);
  margin-bottom: var(--spacing-xs);
}

.score-value {
  font-family: var(--font-mono);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-foreground);
}

/* === Analysis Section === */
.analysis-section {
  margin-bottom: var(--spacing-md);
}

.analysis-content {
  padding: var(--spacing-md);
  background: var(--color-muted);
  border-radius: var(--radius-md);
  white-space: pre-wrap;
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  color: var(--color-foreground-secondary);
  max-height: 300px;
  overflow-y: auto;
}

/* === Mono === */
.mono {
  font-family: var(--font-mono);
}

/* === Responsive === */
@media (max-width: 768px) {
  .detail-meta {
    grid-template-columns: repeat(2, 1fr);
  }

  .scores-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>