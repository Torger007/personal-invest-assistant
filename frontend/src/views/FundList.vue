<template>
  <div class="fund-list">
    <section class="page-header">
      <div>
        <p class="eyebrow">我的资产</p>
        <h2>基金持仓</h2>
        <p class="subtitle">按平台独立管理每一笔基金持仓</p>
      </div>
      <el-button type="primary" size="large" @click="openCreate">+ 新增持仓</el-button>
    </section>

    <el-card class="table-card" shadow="never" v-loading="loading">
      <el-table :data="positions" class="fund-table" empty-text="还没有基金持仓，点击「新增持仓」开始校准" @row-click="openDetail">
        <el-table-column label="资产名称" min-width="270">
          <template #default="{ row }">
            <button class="fund-name" @click.stop="openDetail(row)">{{ row.fund_name }}</button>
            <div class="code">{{ row.fund_code }}</div>
          </template>
        </el-table-column>
        <el-table-column label="实时估值" width="160" align="right">
          <template #default="{ row }">
            <span :class="valueClass(row.estimated_change_pct)">{{ formatPct(row.estimated_change_pct) }}</span>
            <div class="hint">{{ formatMoney(row.current_nav, 4) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="持有收益" width="170" align="right">
          <template #default="{ row }">
            <span :class="valueClass(row.holding_profit)">{{ formatMoney(row.holding_profit) }}</span>
            <div class="hint" :class="valueClass(row.holding_profit_pct)">{{ formatPct(row.holding_profit_pct) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="持有市值" width="160" align="right">
          <template #default="{ row }">{{ formatMoney(row.current_market_value) }}</template>
        </el-table-column>
        <el-table-column label="持仓详情" width="180" align="right">
          <template #default="{ row }">
            <div>{{ formatShares(row.shares) }}</div>
            <div class="hint">@{{ formatMoney(row.avg_cost, 4) }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="platform" label="平台" width="120" />
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openCalibration(row)">校准</el-button>
            <el-button link type="danger" @click.stop="removePosition(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="calibrationVisible" :title="editingPosition ? '校准资产' : '新增持仓'" width="640px" :close-on-click-modal="false" class="calibration-dialog">
      <div class="calibration-copy">
        截至今天（{{ todayLabel }}），我持有
        <el-popover v-model:visible="fundPickerVisible" trigger="click" placement="bottom-start" :width="420" @show="loadHeldFundOptions">
          <template #reference>
            <button type="button" class="fund-picker-trigger" :class="{ placeholder: !form.fund }" :disabled="!!editingPosition">
              {{ form.fund ? `${form.fund.name}（${form.fund.code}）` : '点击选择基金' }}
            </button>
          </template>
          <section class="fund-picker-panel">
            <el-input v-model="fundSearchKeyword" clearable placeholder="搜索基金名称或代码" @input="onFundSearch" />
            <p class="picker-label">{{ fundSearchKeyword ? '搜索结果' : '我持有的基金' }}</p>
            <div v-loading="searching" class="picker-results">
              <button v-for="item in pickerFunds" :key="item.code" type="button" class="picker-option" @click="selectFund(item)">
                <span>{{ item.name }}</span><small>{{ item.code }}</small>
              </button>
              <el-empty v-if="!searching && !pickerFunds.length" :image-size="56" :description="fundSearchKeyword ? '未找到匹配的基金' : '暂无已持有基金，请搜索添加'" />
            </div>
          </section>
        </el-popover>，市值
        <el-input-number v-model="form.marketValue" :min="0.01" :precision="2" controls-position="right" class="inline-number" /> 元，
        目前持有收益为
        <el-input-number v-model="form.holdingProfit" :precision="2" controls-position="right" class="inline-number" /> 元，
        共计
        <el-input-number v-model="form.shares" :min="0.0001" :precision="4" controls-position="right" class="inline-number" /> 份。
      </div>
      <el-alert title="校准将作为今天的绝对基准，重置今天之前的累计计算。" type="warning" :closable="false" show-icon />
      <el-form label-position="left" label-width="64px" class="position-form">
        <el-form-item label="平台" required>
          <el-select v-model="form.platform" :disabled="!!editingPosition" placeholder="选择来源平台" class="full-width">
            <el-option v-for="platform in platforms" :key="platform" :label="platform" :value="platform" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" maxlength="200" show-word-limit placeholder="可选：例如定投策略、账户说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="calibrationVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePosition">{{ editingPosition ? '更新持有资产' : '新增持有资产' }}</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" direction="rtl" size="620px" :with-header="false" @opened="renderChart">
      <section v-if="detail" class="position-drawer">
        <header class="drawer-header">
          <div>
            <h2>{{ detail.fund_name }}</h2>
            <p>{{ detail.fund_code }} <span>·</span> {{ detail.platform }}</p>
          </div>
          <div class="drawer-actions">
            <el-button @click="openCalibration(detail)">校准</el-button>
            <el-button type="danger" plain @click="removePosition(detail)">删除</el-button>
          </div>
        </header>
        <section class="holding-summary">
          <div><span>当前市值</span><strong>{{ formatMoney(detail.current_market_value) }}</strong></div>
          <div><span>持有收益</span><strong :class="valueClass(detail.holding_profit)">{{ formatMoney(detail.holding_profit) }}</strong><small :class="valueClass(detail.holding_profit_pct)">{{ formatPct(detail.holding_profit_pct) }}</small></div>
          <div><span>持有份额</span><strong>{{ formatShares(detail.shares) }}</strong></div>
          <div><span>平均成本</span><strong>{{ formatMoney(detail.avg_cost, 4) }}</strong></div>
        </section>
        <section class="detail-section">
          <h3>持仓信息</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="校准成本">{{ formatMoney(detail.cost_amount) }}</el-descriptions-item>
            <el-descriptions-item label="校准日期">{{ detail.calibrated_at }}</el-descriptions-item>
            <el-descriptions-item label="最新估值">{{ formatMoney(detail.current_nav, 4) }}</el-descriptions-item>
            <el-descriptions-item label="估值涨跌"><span :class="valueClass(detail.estimated_change_pct)">{{ formatPct(detail.estimated_change_pct) }}</span></el-descriptions-item>
            <el-descriptions-item label="数据更新">{{ detail.valuation_updated_at || '--' }}</el-descriptions-item>
            <el-descriptions-item label="备注">{{ detail.remark || '--' }}</el-descriptions-item>
          </el-descriptions>
        </section>
        <section class="detail-section">
          <h3>收益走势</h3>
          <div v-if="detail.history?.length" ref="chartRef" class="chart"></div>
          <el-empty v-else description="已从今天开始记录收益走势" :image-size="80" />
        </section>
      </section>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { fundApi } from '../api'

const positions = ref([])
const loading = ref(false)
const calibrationVisible = ref(false)
const detailVisible = ref(false)
const editingPosition = ref(null)
const detail = ref(null)
const searchResults = ref([])
const heldFundOptions = ref([])
const fundPickerVisible = ref(false)
const fundSearchKeyword = ref('')
const searching = ref(false)
const saving = ref(false)
const chartRef = ref(null)
let chart = null
let fundSearchTimer = null
const platforms = ['支付宝', '天天基金', '银行', '券商', '微信理财通', '其他']
const form = reactive({ fund: null, platform: '', marketValue: undefined, holdingProfit: undefined, shares: undefined, remark: '' })
const todayLabel = computed(() => new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric' }).format(new Date()))

function resetForm() {
  Object.assign(form, { fund: null, platform: '', marketValue: undefined, holdingProfit: undefined, shares: undefined, remark: '' })
  searchResults.value = []
  fundSearchKeyword.value = ''
  fundPickerVisible.value = false
}
function formatMoney(value, digits = 2) { return value === null || value === undefined ? '--' : `¥${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })}` }
function formatShares(value) { return value === null || value === undefined ? '--' : `${Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 4 })} 份` }
function formatPct(value) { return value === null || value === undefined ? '--' : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(2)}%` }
function valueClass(value) { return Number(value) > 0 ? 'up' : Number(value) < 0 ? 'down' : '' }

async function loadPositions() {
  loading.value = true
  try { positions.value = (await fundApi.getList()).data.positions || [] } catch { ElMessage.error('加载持仓失败') } finally { loading.value = false }
}
function openCreate() { editingPosition.value = null; resetForm(); calibrationVisible.value = true }
function openCalibration(position) {
  editingPosition.value = position
  Object.assign(form, { fund: { code: position.fund_code, name: position.fund_name }, platform: position.platform, marketValue: position.current_market_value, holdingProfit: position.holding_profit, shares: position.shares, remark: position.remark || '' })
  fundPickerVisible.value = false
  fundSearchKeyword.value = ''
  calibrationVisible.value = true
}
const pickerFunds = computed(() => fundSearchKeyword.value.trim() ? searchResults.value : heldFundOptions.value)
async function loadHeldFundOptions() {
  if (editingPosition.value) return
  fundSearchKeyword.value = ''
  searchResults.value = []
  searching.value = true
  try { heldFundOptions.value = (await fundApi.getOptions()).data.funds || [] } catch { ElMessage.error('加载已持有基金失败') } finally { searching.value = false }
}
function onFundSearch(keyword) {
  clearTimeout(fundSearchTimer)
  if (!keyword?.trim()) { searchResults.value = []; return }
  fundSearchTimer = setTimeout(() => searchFunds(keyword), 250)
}
async function searchFunds(keyword) {
  searching.value = true
  try { searchResults.value = (await fundApi.search(keyword.trim())).data.funds || [] } catch { ElMessage.error('基金搜索失败，请稍后重试') } finally { searching.value = false }
}
function selectFund(fund) {
  form.fund = { code: fund.code, name: fund.name }
  fundPickerVisible.value = false
}
async function savePosition() {
  if (!form.fund || !form.platform || !form.marketValue || form.holdingProfit === undefined || !form.shares) { ElMessage.warning('请完整填写基金、市值、收益、份额和平台'); return }
  const payload = { fund_code: form.fund.code, fund_name: form.fund.name, platform: form.platform, market_value: form.marketValue, holding_profit: form.holdingProfit, shares: form.shares, remark: form.remark }
  saving.value = true
  try {
    if (editingPosition.value) await fundApi.calibrate(editingPosition.value.id, payload)
    else await fundApi.create(payload)
    ElMessage.success(editingPosition.value ? '持仓已按今天的数据校准' : '持仓已新增')
    calibrationVisible.value = false
    await loadPositions()
    if (detailVisible.value && editingPosition.value) await openDetail(positions.value.find(item => item.id === editingPosition.value.id))
  } catch (error) { ElMessage.error(error.response?.data?.detail || '保存持仓失败') } finally { saving.value = false }
}
async function openDetail(position) {
  if (!position) return
  detailVisible.value = true
  try { detail.value = (await fundApi.getDetail(position.id)).data; await nextTick(); renderChart() } catch { ElMessage.error('加载持仓详情失败') }
}
async function removePosition(position) {
  try {
    await ElMessageBox.confirm(`确认删除「${position.fund_name} · ${position.platform}」这笔持仓？`, '删除持仓', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    await fundApi.remove(position.id)
    ElMessage.success('持仓已删除')
    if (detail.value?.id === position.id) { detailVisible.value = false; detail.value = null }
    await loadPositions()
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error('删除持仓失败') }
}
function renderChart() {
  if (!chartRef.value || !detail.value?.history?.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  const history = detail.value.history
  chart.setOption({ tooltip: { trigger: 'axis' }, legend: { data: ['持有市值', '持有收益'] }, grid: { left: 56, right: 24, top: 42, bottom: 38 }, xAxis: { type: 'category', data: history.map(item => item.date) }, yAxis: { type: 'value', scale: true }, series: [{ name: '持有市值', type: 'line', smooth: true, data: history.map(item => item.market_value), lineStyle: { color: '#59728f' } }, { name: '持有收益', type: 'line', smooth: true, data: history.map(item => item.holding_profit), lineStyle: { color: '#d85040' } }] })
}
onMounted(loadPositions)
onBeforeUnmount(() => { clearTimeout(fundSearchTimer); chart?.dispose() })
</script>

<style scoped>
.fund-list { max-width: 1440px; margin: 0 auto; padding: 24px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.eyebrow { margin: 0 0 4px; color: var(--color-primary); font-size: 13px; font-weight: 600; }.page-header h2 { margin: 0; font-size: 28px; }.subtitle { color: var(--color-foreground-muted); margin: 7px 0 0; }.table-card { border-radius: 16px; }.fund-name { border: 0; padding: 0; color: var(--color-foreground); background: none; cursor: pointer; font-size: 16px; font-weight: 650; text-align: left; }.fund-name:hover { color: var(--color-primary); }.code, .hint { margin-top: 5px; color: var(--color-foreground-muted); font-size: 13px; }.up { color: var(--color-up); }.down { color: var(--color-down); }
.calibration-copy { color: var(--color-foreground); font-size: 20px; line-height: 2.6; margin: 6px 0 22px; }.fund-picker-trigger { width: 250px; min-height: 38px; padding: 0 12px; border: 0; border-bottom: 2px solid #94a3b8; background: transparent; color: var(--color-foreground); cursor: pointer; font: inherit; text-align: left; vertical-align: middle; }.fund-picker-trigger.placeholder { color: var(--color-foreground-muted); }.fund-picker-trigger:disabled { cursor: default; }.fund-picker-panel { padding: 4px; }.picker-label { margin: 14px 0 8px; color: var(--color-foreground-muted); font-size: 13px; }.picker-results { min-height: 100px; max-height: 250px; overflow-y: auto; }.picker-option { display: flex; width: 100%; align-items: center; justify-content: space-between; gap: 16px; border: 0; border-radius: 6px; padding: 10px; background: transparent; color: var(--color-foreground); cursor: pointer; text-align: left; }.picker-option:hover { background: var(--color-muted); }.picker-option small { flex: 0 0 auto; color: var(--color-foreground-muted); }.inline-number { width: 122px; vertical-align: middle; }.position-form { margin-top: 28px; }.full-width { width: 100%; }
.position-drawer { padding: 30px; }.drawer-header { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; border-bottom: 1px solid var(--color-border); padding-bottom: 20px; }.drawer-header h2 { margin: 0 0 8px; font-size: 24px; }.drawer-header p { margin: 0; color: var(--color-foreground-muted); }.drawer-header span { padding: 0 5px; }.drawer-actions { display: flex; }.holding-summary { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1px; background: var(--color-border); margin: 24px 0; border: 1px solid var(--color-border); border-radius: 12px; overflow: hidden; }.holding-summary div { min-height: 100px; padding: 16px; background: var(--color-surface); }.holding-summary span, .holding-summary small { display: block; color: var(--color-foreground-muted); font-size: 13px; }.holding-summary strong { display: block; margin-top: 8px; font-size: 21px; }.holding-summary small { margin-top: 4px; }.detail-section { margin-top: 28px; }.detail-section h3 { margin: 0 0 14px; font-size: 16px; }.chart { height: 300px; }
@media (max-width: 720px) { .fund-list { padding: 16px; }.page-header { align-items: flex-start; gap: 16px; flex-direction: column; }.calibration-copy { font-size: 16px; line-height: 2.8; }.fund-picker-trigger { width: 100%; }.inline-number { width: 130px; }.drawer-header { flex-direction: column; }.position-drawer { padding: 20px; } }
</style>
