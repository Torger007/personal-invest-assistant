<template>
  <div class="market-overview">
    <h2>市场概览</h2>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>上证指数</span>
          </template>
          <div class="index-value">--</div>
          <div class="index-change">--</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>深证成指</span>
          </template>
          <div class="index-value">--</div>
          <div class="index-change">--</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>创业板指</span>
          </template>
          <div class="index-value">--</div>
          <div class="index-change">--</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px;">
      <template #header>
        <span>市场状态</span>
      </template>
      <p>系统正在初始化，请先配置数据源...</p>
    </el-card>
  </div>
</template>

<script setup>
</script>

<style scoped>
.market-overview {
  padding: 20px;
}

.index-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.index-change {
  font-size: 14px;
  margin-top: 8px;
}
</style>
