<template>
  <div class="fund-list">
    <div class="page-header">
      <h2>基金分析</h2>
      <div class="search-box">
        <el-input
          v-model="searchCode"
          placeholder="输入基金代码查询（如 005827）"
          class="search-input"
          @keyup.enter="searchFund"
          clearable
        >
          <template #prefix>
            <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="M21 21l-4.35-4.35"/>
            </svg>
          </template>
        </el-input>
        <el-button type="primary" @click="searchFund" class="search-btn">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          查询
        </el-button>
      </div>
    </div>

    <el-card class="table-card" v-loading="loading">
      <el-table :data="funds" stripe class="fund-table" :row-class-name="tableRowClassName">
        <el-table-column prop="code" label="基金代码" width="140">
          <template #default="{ row }">
            <span class="code-cell mono">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="基金名称">
          <template #default="{ row }">
            <div class="name-cell">
              <span class="fund-name">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="140">
          <template #default="{ row }">
            <el-tag size="small" class="type-tag">{{ row.type || '--' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center">
          <template #default="{ row }">
            <el-button size="small" @click="goDetail(row.code)" class="detail-btn">
              <svg class="btn-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && funds.length === 0" description="暂无基金数据" />
    </el-card>

    <!-- 查询结果 -->
    <el-dialog v-model="showResult" title="查询结果" width="420px" class="result-dialog">
      <div class="result-content" v-if="searchResult">
        <div class="result-icon success">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 6L9 17l-5-5"/>
          </svg>
        </div>
        <div class="result-text">
          <p class="result-title">找到基金</p>
          <p class="result-name">{{ searchResult.name }}</p>
          <p class="result-code mono">{{ searchResult.code }}</p>
        </div>
      </div>
      <div class="result-content" v-else>
        <div class="result-icon error">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M15 9l-6 6M9 9l6 6"/>
          </svg>
        </div>
        <div class="result-text">
          <p class="result-title">未找到基金</p>
          <p class="result-desc">请确认基金代码是否正确</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fundApi } from '../api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const funds = ref([])
const loading = ref(false)
const searchCode = ref('')
const showResult = ref(false)
const searchResult = ref(null)

const loadFunds = async () => {
  loading.value = true
  try {
    const { data } = await fundApi.getList()
    funds.value = data.funds || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const searchFund = async () => {
  if (!searchCode.value.trim()) return
  try {
    const { data } = await fundApi.getDetail(searchCode.value.trim())
    if (data.error) {
      searchResult.value = null
    } else {
      searchResult.value = data
      router.push(`/funds/${searchCode.value.trim()}`)
    }
    showResult.value = true
  } catch (e) {
    ElMessage.error('查询失败')
  }
}

const goDetail = (code) => {
  router.push(`/funds/${code}`)
}

const tableRowClassName = ({ rowIndex }) => {
  return rowIndex % 2 === 0 ? 'even-row' : 'odd-row'
}

onMounted(loadFunds)
</script>

<style scoped>
.fund-list {
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
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.page-header h2 {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-foreground);
}

.search-box {
  display: flex;
  gap: var(--spacing-sm);
}

.search-input {
  width: 320px;
}

.search-input :deep(.el-input__wrapper) {
  padding-left: 12px;
}

.input-icon {
  width: 18px;
  height: 18px;
  color: var(--color-foreground-muted);
}

.search-btn {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-icon {
  width: 18px;
  height: 18px;
}

/* === Table Card === */
.table-card {
  border-radius: var(--radius-lg);
}

.fund-table .code-cell {
  font-family: var(--font-mono);
  font-weight: var(--font-weight-medium);
  color: var(--color-primary);
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.fund-name {
  font-weight: var(--font-weight-medium);
  color: var(--color-foreground);
}

.type-tag {
  border-radius: var(--radius-full);
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

/* === Result Dialog === */
.result-dialog :deep(.el-dialog__body) {
  padding: var(--spacing-lg);
}

.result-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  padding: var(--spacing-md);
}

.result-icon {
  flex-shrink: 0;
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
}

.result-icon svg {
  width: 28px;
  height: 28px;
}

.result-icon.success {
  background: rgba(22, 163, 74, 0.1);
  color: var(--color-success);
}

.result-icon.error {
  background: rgba(220, 38, 38, 0.1);
  color: var(--color-destructive);
}

.result-text {
  flex: 1;
}

.result-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-foreground);
  margin: 0 0 4px 0;
}

.result-name {
  font-size: var(--font-size-base);
  color: var(--color-foreground-secondary);
  margin: 0;
}

.result-code {
  font-size: var(--font-size-sm);
  color: var(--color-foreground-muted);
  margin: 4px 0 0 0;
}

.result-desc {
  font-size: var(--font-size-sm);
  color: var(--color-foreground-muted);
  margin: 0;
}

/* === Mono === */
.mono {
  font-family: var(--font-mono);
}

/* === Responsive === */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .search-box {
    flex-direction: column;
  }

  .search-input {
    width: 100%;
  }
}
</style>