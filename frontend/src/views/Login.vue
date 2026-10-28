<template>
  <div class="login-wrap">
    <div class="card login-card">
      <h2>AI 成本监控</h2>
      <p class="slogan">🔐 Key 只存在你的浏览器里，服务器见不到、存不了</p>
      <form @submit.prevent="submit">
        <input v-model="email" type="email" placeholder="邮箱" required />
        <input v-model="password" type="password" placeholder="密码（至少8位）" required minlength="8" />
        <button class="btn" :disabled="loading">{{ isLogin ? '登录' : '注册' }}</button>
      </form>
      <a href="#" @click.prevent="isLogin = !isLogin">
        {{ isLogin ? '没有账号？去注册' : '已有账号？去登录' }}
      </a>
      <p v-if="err" class="err">{{ err }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../lib/api'

const router = useRouter()
const email = ref('')
const password = ref('')
const isLogin = ref(true)
const loading = ref(false)
const err = ref('')

async function submit() {
  loading.value = true
  err.value = ''
  try {
    const url = isLogin.value ? '/auth/login' : '/auth/register'
    const { data } = await api.post(url, { email: email.value, password: password.value })
    localStorage.setItem('acm_token', data.token)
    api.defaults.headers.common['Authorization'] = `Bearer ${data.token}`
    router.push('/')
  } catch (e) {
    err.value = e.response?.data?.detail || '请求失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap { display: flex; justify-content: center; padding-top: 10vh; }
.login-card { width: 360px; display: flex; flex-direction: column; gap: 12px; }
.login-card form { display: flex; flex-direction: column; gap: 10px; }
.slogan { color: #2a9d4a; font-size: 13px; }
.err { color: #e05252; font-size: 13px; }
</style>
