<template>
  <div>
    <div class="card" v-if="accounts.length === 0">
      还没有账户，去 <router-link to="/accounts">账户管理</router-link> 添加一个
    </div>
    <div v-for="a in accounts" :key="a.id" class="card">
      <h3>{{ a.name }} <small>{{ a.provider }}</small></h3>
      <!-- TODO: 快照趋势图（echarts）+ 烧钱速率 + 额度还剩 N 天预测 -->
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api, collectAccount } from '../lib/api'

const accounts = ref([])

onMounted(async () => {
  try {
    const { data } = await api.get('/accounts')
    accounts.value = data
    // 打开页面自动采集：从本地保险箱取 Key 触发（口令 demo 用占位，后续接登录会话）
    for (const a of accounts.value) {
      collectAccount(a.id, 'session').catch(() => {})
    }
  } catch { /* 后端未启动时静默 */ }
})
</script>
