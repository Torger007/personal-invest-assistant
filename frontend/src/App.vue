<template>
  <el-container>
    <el-header>
      <h1>个人投资助手</h1>
      <el-menu mode="horizontal" :router="true">
        <el-menu-item index="/">市场概览</el-menu-item>
        <el-menu-item index="/funds">基金分析</el-menu-item>
        <el-menu-item index="/sectors">板块走势</el-menu-item>
        <el-menu-item index="/advice">投资建议</el-menu-item>
      </el-menu>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
</script>

<style>
#app {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}

.el-header {
  display: flex;
  align-items: center;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.el-header h1 {
  margin: 0 20px 0 0;
  font-size: 20px;
  color: #303133;
}
</style>
