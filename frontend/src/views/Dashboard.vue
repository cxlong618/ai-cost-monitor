<template>
  <div>
    <div class="card" v-if="accounts.length === 0">
      还没有账户，去 <router-link to="/accounts">账户管理</router-link> 添加一个
    </div>

    <div v-for="a in accounts" :key="a.id" class="card">
      <div class="acc-head">
        <h3>{{ a.name }} <small>{{ a.provider }}</small></h3>
        <span v-if="a.days_left !== null" :class="a.days_left < 3 ? 'warn' : ''">
          ⏳ 额度还剩约 {{ a.days_left }} 天
        </span>
      </div>
      <div class="metrics">
        <div>余额：<b>¥{{ a.latest_balance ?? '—' }}</b></div>
        <div v-if="a.burn_rate">日均消耗：¥{{ a.burn_rate.toFixed(2) }}</div>
      </div>
      <v-chart v-if="a.points?.length" :option="chartOption(a)" autoresize style="height:240px" />
      <p v-else class="hint">暂无快照数据（账户模式为本地 Key 时，打开本页会自动采集一次）</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { api, collectAccount } from '../lib/api'

use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const accounts = ref([])

function chartOption(a) {
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'time' },
    yAxis: { type: 'value', scale: true },
    series: [{
      type: 'line',
      smooth: true,
      data: a.points.filter(p => p.balance != null).map(p => [p.t, p.balance]),
      areaStyle: { opacity: 0.12 },
    }],
  }
}

onMounted(async () => {
  try {
    const { data } = await api.get('/accounts')
    accounts.value = data
    for (const a of data) {
      // 本地 Key 模式：打开页面自动采集一次
      collectAccount(a.id, 'session').catch(() => {})
      // 拉趋势
      api.get(`/trends/${a.id}`).then(({ data: t }) => {
        Object.assign(a, t)
      })
    }
  } catch (e) {
    if (e.response?.status === 401) location.href = '/login'
  }
})
</script>

<style scoped>
.acc-head { display: flex; justify-content: space-between; align-items: center; }
.metrics { display: flex; gap: 24px; margin: 10px 0; color: #555; }
.warn { color: #e05252; font-weight: 600; }
.hint { color: #999; font-size: 13px; }
</style>
