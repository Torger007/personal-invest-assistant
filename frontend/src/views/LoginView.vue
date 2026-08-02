<template>
  <main class="login-page">
    <el-card class="login-card" shadow="never">
      <h1>个人投资助手</h1>
      <p>登录后访问你的持仓、建议和 AI 会话。</p>
      <el-form :model="form" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model.trim="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" @keyup.enter="submit" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" class="submit">登录</el-button>
      </el-form>
    </el-card>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '../api'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function submit() {
  if (!form.username || !form.password) return ElMessage.warning('请输入用户名和密码')
  loading.value = true
  try {
    await authApi.login(form.username, form.password)
    await router.replace(typeof route.query.redirect === 'string' ? route.query.redirect : '/')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; display: grid; place-items: center; background: var(--color-background, #f6f8fb); padding: 24px; }
.login-card { width: min(100%, 400px); }
h1 { margin: 0 0 8px; color: var(--color-foreground, #1f2937); }
p { margin: 0 0 24px; color: var(--color-foreground-secondary, #6b7280); line-height: 1.6; }
.submit { width: 100%; }
</style>
