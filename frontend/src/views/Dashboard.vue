<template>
  <div>
    <div class="page-head">
      <h2>仪表盘</h2>
      <select v-model.number="days" @change="refresh(false)"><option :value="7">最近 7 天</option><option :value="30">最近 30 天</option><option :value="90">最近 90 天</option></select>
      <button class="btn" :disabled="loading" @click="refresh(true)">刷新 / 采集</button>
      <span class="badge badge-blue" v-if="accounts.length">{{ accounts.length }} 个账户</span>
    </div>

    <div class="card empty" v-if="!loading && accounts.length === 0">
      <div class="empty-inner">
        <div class="empty-ico">🔌</div>
        <h3>还没有账户</h3>
        <p class="sub">添加你的第一家 AI 厂商，开始监控成本</p>
        <router-link to="/accounts"><button class="btn">+ 添加账户</button></router-link>
      </div>
    </div>

    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="notice" class="hint">{{ notice }}</p>
    <!-- 总览统计 -->
    <div class="stat-grid" v-if="accounts.length">
      <div class="stat">
        <div class="label">账户总数</div>
        <div class="value">{{ accounts.length }}</div>
      </div>
      <div class="stat">
        <div class="label">余额合计</div>
        <div class="value" v-for="(value, currency) in totals('latest_balance')" :key="currency">{{ currency }} {{ value.toFixed(2) }}</div>
      </div>
      <div class="stat">
        <div class="label">日均总消耗</div>
        <div class="value" v-for="(value, currency) in totals('burn_rate_per_day')" :key="currency">{{ currency }} {{ value.toFixed(2) }}<span class="unit">/天</span></div>
      </div>
    </div>

    <div v-for="a in accounts" :key="a.id" class="card account-card">
      <div class="acc-head">
        <div class="acc-title">
          <span class="provider-dot" :class="a.provider"></span>
          <h3>{{ a.name }}</h3>
          <span class="badge badge-gray">{{ a.provider }}</span>
          <span class="badge" :class="statusBadge(a)">{{ statusText(a) }}</span>
        </div>
        <span v-if="a.days_left !== null && a.days_left !== undefined" class="days-left" :class="{ danger: a.days_left < 3 }">
          ⏳ 约 {{ a.days_left }} 天耗尽
        </span>
      </div>

      <div class="acc-metrics">
        <div class="metric" v-if="a.latest_balance != null">
          <span class="m-label">余额</span>
          <b class="m-value">{{ a.currency || '未知币种' }} {{ a.latest_balance }}</b>
        </div>
        <div class="metric" v-if="a.latest_quota_pct != null">
          <span class="m-label">配额已用</span>
          <b class="m-value">{{ a.latest_quota_pct }}%</b>
          <div class="progress"><i :style="{ width: a.latest_quota_pct + '%' }" :class="a.latest_quota_pct > 80 ? 'high' : ''"></i></div>
        </div>
        <div class="metric" v-if="a.burn_rate_per_day != null">
          <span class="m-label">日均消耗</span>
          <b class="m-value">{{ a.currency }} {{ a.burn_rate_per_day.toFixed(2) }}</b>
        </div>
        <div class="metric" v-if="a.latest_cost_today != null"><span class="m-label">今日成本</span><b>{{ a.currency }} {{ a.latest_cost_today }}</b></div>
        <div class="metric" v-if="a.latest_cost_month != null"><span class="m-label">本月成本</span><b>{{ a.currency }} {{ a.latest_cost_month }}</b></div>
      </div>

      <v-chart v-if="a.points?.length > 1" :option="chartOption(a)" autoresize class="chart" />
      <p v-else class="hint">快照不足 2 个，暂无法画趋势（多采集几次即可）</p>
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
import { api, collectAccount, errorMessage } from '../lib/api'
import { vaultUnlocked, hasKey } from '../lib/keyStore'

use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const accounts = ref([])
const loading = ref(true)
const days = ref(30)
const error = ref('')
const notice = ref('')

function totals(field) {
  return accounts.value.reduce((out, a) => {
    if (a[field] != null) {
      const currency = a.currency || '未知币种'
      out[currency] = (out[currency] || 0) + a[field]
    }
    return out
  }, {})
}

const statusText = (a) => ['正常', 'Key 失效', '采集失败', ''][a.status] || ''
const statusBadge = (a) => a.status === 0 ? 'badge-green' : 'badge-red'

function chartOption(a) {
  const fields = [
    ['balance', `余额 (${a.currency || '未知币种'})`, 0],
    ['quota_pct', '配额已用 (%)', 1],
    ['cost_today', `当日累计成本 (${a.currency || '未知币种'})`, 0],
  ]
  return {
    tooltip: { trigger: 'axis', backgroundColor: '#fff', borderColor: '#e8ecf4', textStyle: { color: '#1a2233', fontSize: 12 } },
    grid: { left: 60, right: 44, top: 14, bottom: 28 },
    xAxis: { type: 'time', axisLine: { lineStyle: { color: '#e8ecf4' } }, axisLabel: { color: '#9aa4bd', fontSize: 11 } },
    yAxis: [{ type: 'value', scale: true }, { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%' }, show: a.latest_quota_pct != null }],
    series: fields.filter(([field]) => a.points.some(p => p[field] != null)).map(([field, name, axis]) => ({
      name, yAxisIndex: axis,
      type: 'line', smooth: 0.35, symbolSize: 5,
      lineStyle: { width: 2.5, color: '#4f6ef7' },
      itemStyle: { color: '#4f6ef7' },
      areaStyle: {
        opacity: 0.12,
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
          { offset: 0, color: '#7c5cff' }, { offset: 1, color: 'rgba(124,92,255,0)' },
        ]},
      },
      data: a.points.map(p => [p.t, p[field] ?? null]),
    })),
  }
}

async function refresh(collect = false) {
  if (loading.value && accounts.value.length) return
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    const { data } = await api.get('/accounts')
    const failures = []
    await Promise.all(data.map(async (a) => {
      if (collect && a.mode === 0) {
        if (!vaultUnlocked()) notice.value = '本地保险箱已锁定，请到账户管理解锁后采集；当前显示历史数据。'
        else {
          try { if (await hasKey(a.id)) await collectAccount(a.id); else failures.push(`${a.name}：尚未保存本地 Key`) }
          catch (e) { failures.push(`${a.name}：${errorMessage(e)}`) }
        }
      }
      try {
        const { data: t } = await api.get(`/trends/${a.id}`, { params: { days: days.value } })
        Object.assign(a, t)
      } catch (e) { failures.push(`${a.name}：${errorMessage(e)}`) }
    }))
    accounts.value = data
    error.value = failures.join('；')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
onMounted(() => refresh(true))
</script>

<style scoped>
.page-head { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-bottom: 18px; }
.page-head h2 { font-size: 20px; }
.empty { text-align: center; padding: 60px 20px; }
.empty-ico { font-size: 44px; margin-bottom: 12px; }
.empty .sub { color: var(--text-3); margin: 6px 0 18px; }
.account-card .acc-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.acc-title { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.provider-dot { width: 10px; height: 10px; border-radius: 3px; }
.provider-dot.deepseek { background: #4d6bfe; }
.provider-dot.zai { background: #3859ff; }
.provider-dot.openrouter { background: #8b5cf6; }
.provider-dot.anthropic { background: #d97757; }
.provider-dot.openai { background: #10a37f; }
.provider-dot.siliconflow { background: #6366f1; }
.days-left { font-size: 13px; color: var(--success); font-weight: 500; }
.days-left.danger { color: var(--danger); }
.acc-metrics { display: flex; gap: 40px; margin: 4px 0 12px; flex-wrap: wrap; }
.metric { display: flex; flex-direction: column; gap: 4px; }
.m-label { font-size: 12px; color: var(--text-3); }
.m-value { font-size: 22px; font-weight: 700; letter-spacing: -0.02em; }
.progress { width: 140px; height: 6px; background: var(--surface-2); border-radius: 3px; overflow: hidden; }
.progress i { display: block; height: 100%; background: var(--primary-grad); border-radius: 3px; }
.progress i.high { background: linear-gradient(90deg, #f59e0b, #e05252); }
.chart { height: 240px; }
</style>
