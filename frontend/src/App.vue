<template>
  <div class="layout" v-if="$route.name !== 'login'">
    <aside class="sidebar">
      <div class="logo">
        <span class="logo-icon">◈</span>
        <div>
          <b>成本监控</b>
          <small>AI Cost Monitor</small>
        </div>
      </div>
      <nav>
        <router-link to="/"><span class="ico">📊</span>仪表盘</router-link>
        <router-link to="/accounts"><span class="ico">🔌</span>账户管理</router-link>
        <router-link to="/alerts"><span class="ico">🔔</span>告警规则</router-link>
        <router-link to="/calculator"><span class="ico">🧮</span>订阅计算器</router-link>
      </nav>
      <div class="sidebar-foot">
        <div class="trust">
          <div>🔐 Key 只存在你的浏览器</div>
          <div>后端仅内存中转，不落库</div>
        </div>
        <button class="logout" @click="logout">退出登录</button>
      </div>
    </aside>
    <main class="content">
      <router-view />
    </main>
  </div>
  <router-view v-else />
</template>

<script setup>
import { useRouter } from 'vue-router'
import { api } from './lib/api'
import { lockVault } from './lib/keyStore'

const router = useRouter()
function logout() {
  localStorage.removeItem('acm_token')
  localStorage.removeItem('acm_user_id')
  lockVault()
  delete api.defaults.headers.common['Authorization']
  router.push('/login')
}
</script>

<style scoped>
.layout { display: flex; min-height: 100vh; }
.sidebar {
  width: 232px; flex-shrink: 0;
  background: linear-gradient(180deg, #141a2e 0%, #1a2138 100%);
  color: #e6e9f5;
  display: flex; flex-direction: column;
  padding: 22px 14px;
}
.logo { display: flex; gap: 10px; align-items: center; padding: 0 10px 22px; border-bottom: 1px solid rgba(255,255,255,0.07); }
.logo-icon {
  width: 38px; height: 38px; display: grid; place-items: center;
  background: linear-gradient(135deg, #4f6ef7, #7c5cff); border-radius: 11px;
  font-size: 18px; color: #fff;
}
.logo b { font-size: 15px; display: block; }
.logo small { color: #7b86a8; font-size: 11px; }

nav { display: flex; flex-direction: column; gap: 4px; margin-top: 18px; }
nav a {
  display: flex; align-items: center; gap: 10px;
  color: #97a1c0; text-decoration: none;
  padding: 11px 12px; border-radius: 10px; font-size: 14px;
  transition: all 0.15s;
}
nav a:hover { color: #fff; background: rgba(255,255,255,0.05); }
nav a.router-link-active {
  color: #fff; background: linear-gradient(135deg, rgba(79,110,247,0.35), rgba(124,92,255,0.35));
  box-shadow: inset 0 0 0 1px rgba(140,160,255,0.25);
}
.ico { font-size: 15px; width: 20px; text-align: center; }

.sidebar-foot { margin-top: auto; display: flex; flex-direction: column; gap: 10px; }
.trust {
  background: rgba(79,110,247,0.12); border: 1px solid rgba(124,92,255,0.25);
  border-radius: 10px; padding: 10px 12px;
  font-size: 12px; color: #aab5d8; line-height: 1.7;
}
.logout {
  background: transparent; border: 1px solid rgba(255,255,255,0.12);
  color: #97a1c0; border-radius: 10px; padding: 9px; cursor: pointer; font-size: 13px;
  transition: all 0.15s;
}
.logout:hover { color: #fff; border-color: rgba(255,255,255,0.3); }

.content { flex: 1; padding: 26px 30px; max-width: 1200px; }
.content { min-width: 0; }
@media (max-width: 768px) {
  .layout { flex-direction: column; }
  .sidebar { width: 100%; padding: 12px; }
  .logo, .trust { display: none; }
  nav { flex-direction: row; flex-wrap: wrap; margin-top: 0; }
  nav a { padding: 8px; }
  .sidebar-foot { margin-top: 8px; }
  .content { padding: 16px; }
}
</style>
