<template>
  <div class="layout">
    <aside class="sidebar">
      <h1 class="logo">💰 AI 成本监控</h1>
      <nav>
        <router-link to="/">仪表盘</router-link>
        <router-link to="/accounts">账户管理</router-link>
        <router-link to="/alerts">告警规则</router-link>
        <router-link to="/calculator">订阅计算器</router-link>
        <a href="#" @click.prevent="logout">退出登录</a>
      </nav>
      <footer class="trust">
        🔐 Key 只存在你的浏览器里<br />服务器见不到、存不了
      </footer>
    </aside>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { api } from './lib/api'

const router = useRouter()
function logout() {
  localStorage.removeItem('acm_token')
  delete api.defaults.headers.common['Authorization']
  router.push('/login')
}
</script>

<style scoped>
.layout { display: flex; min-height: 100vh; }
.sidebar {
  width: 220px; padding: 20px; background: #1a1f2e; color: #e6e9f0;
  display: flex; flex-direction: column;
}
.logo { font-size: 18px; margin-bottom: 24px; }
nav { display: flex; flex-direction: column; gap: 8px; }
nav a { color: #9aa4bf; text-decoration: none; padding: 8px 12px; border-radius: 8px; }
nav a.router-link-active { background: #2a3149; color: #fff; }
.trust { margin-top: auto; font-size: 12px; color: #6b7499; line-height: 1.6; }
.content { flex: 1; padding: 24px; }
</style>
