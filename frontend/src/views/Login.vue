<template>
  <div class="login-page">
    <div class="login-visual">
      <div class="visual-inner">
        <h1>你的 AI 账单<br />一目了然</h1>
        <p>多家 AI 厂商余额 · 配额 · 消耗速率，一个仪表盘全掌握</p>
        <ul>
          <li>🔐 Key 只存浏览器，服务器碰不到</li>
          <li>📈 烧钱速率与额度预测</li>
          <li>🔔 阈值告警，余额告急早知道</li>
        </ul>
      </div>
    </div>
    <div class="login-panel">
      <div class="login-card">
        <h2>{{ isLogin ? '欢迎回来' : '创建账号' }}</h2>
        <p class="sub">{{ isLogin ? '登录你的成本监控面板' : '30 秒开始监控你的 AI 开销' }}</p>
        <form @submit.prevent="submit">
          <label>邮箱</label>
          <input v-model="email" type="email" placeholder="you@example.com" required />
          <label>密码</label>
          <input v-model="password" type="password" placeholder="至少 8 位" required minlength="8" />
          <button class="btn btn-block" :disabled="loading">
            {{ loading ? '请稍候…' : isLogin ? '登 录' : '注 册' }}
          </button>
        </form>
        <a class="switch" href="#" @click.prevent="isLogin = !isLogin">
          {{ isLogin ? '没有账号？去注册 →' : '已有账号？去登录 →' }}
        </a>
        <p v-if="err" class="err">{{ err }}</p>
      </div>
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
    err.value = e.response?.data?.detail || '请求失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { display: flex; min-height: 100vh; }
.login-visual {
  flex: 1.1;
  background: linear-gradient(150deg, #141a2e 0%, #232c54 55%, #37306e 100%);
  color: #eef0fa;
  display: flex; align-items: center; justify-content: center;
  padding: 40px;
}
.visual-inner { max-width: 420px; }
.visual-inner h1 { font-size: 38px; line-height: 1.25; letter-spacing: -0.02em; margin-bottom: 14px; }
.visual-inner p { color: #9aa5cc; font-size: 15px; line-height: 1.7; margin-bottom: 28px; }
.visual-inner ul { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.visual-inner li {
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.09);
  padding: 12px 16px; border-radius: 12px; font-size: 14px;
}
.login-panel { flex: 1; display: flex; align-items: center; justify-content: center; padding: 40px; }
.login-card { width: 100%; max-width: 360px; }
.login-card h2 { font-size: 24px; margin-bottom: 4px; }
.sub { color: var(--text-3); margin-bottom: 22px; }
form { display: flex; flex-direction: column; gap: 8px; }
label { font-size: 12px; color: var(--text-2); font-weight: 500; margin-top: 8px; }
.btn-block { width: 100%; margin-top: 16px; padding: 12px; font-size: 15px; }
.switch { display: block; text-align: center; margin-top: 18px; font-size: 13px; }
.err { color: var(--danger); font-size: 13px; text-align: center; margin-top: 12px; }
@media (max-width: 768px) { .login-visual { display: none; } }
</style>
