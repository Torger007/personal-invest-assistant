<template>
  <div class="fund-list">
    <div class="header">
      <h2>基金分析</h2>
      <el-input
        v-model="searchCode"
        placeholder="输入基金代码查询（如 005827）"
        style="width: 280px;"
        @keyup.enter="searchFund"
      >
        <template #append>
          <el-button @click="searchFund">查询</el-button>
        </template>
      </el-input>
    </div>

    <el-card>
      <el-table :data="funds" stripe v-loading="loading">
        <el-table-column prop="code" label="基金代码" width="120" />
        <el-table-column prop="name" label="基金名称" />
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" @click="goDetail(row.code)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && funds.length === 0" description="暂无基金数据" />
    </el-card>

    <!-- 查询结果（按代码直接跳转） -->
    <el-dialog v-model="showResult" title="查询结果" width="400px">
      <p v-if="searchResult">找到基金：{{ searchResult.name }} ({{ searchResult.code }})</p>
      <p v-else>未找到该基金，请确认代码正确</p>
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
      // 直接跳转详情页
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

onMounted(loadFunds)
</script>

<style scoped>
.fund-list {
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