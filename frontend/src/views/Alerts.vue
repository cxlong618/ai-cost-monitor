<template>
  <div>
    <h2 style="margin-bottom:16px">告警规则</h2>
    <div class="card">
      <h3>新建规则</h3>
      <form @submit.prevent="add" class="form-row">
        <select v-model="form.account_id" required>
          <option value="" disabled>选择账户</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}（{{ a.provider }}）</option>
        </select>
        <select v-model="form.type">
          <option :value="0">余额低于（账户币种）</option>
          <option :value="1">配额消耗超过（%）</option>
          <option :value="2">日均余额消耗超过（账户币种/天）</option>
        </select>
        <input v-model.number="form.threshold" type="number" step="0.01" placeholder="阈值" required />
        <button class="btn" :disabled="loading">添加</button>
      </form>
      <p class="hint">免费版每账户 1 条启用规则，Pro 最多 20 条。当前支持站内通知，速率为近 30 天余额日均消耗，非环比涨幅。</p>
      <p v-if="error" role="alert">{{ error }}</p>
    </div>

    <div class="card">
      <h3>我的规则</h3>
      <table class="tbl" v-if="rules.length">
        <tr><th>账户</th><th>类型</th><th>阈值</th><th>状态</th><th></th></tr>
        <tr v-for="r in rules" :key="r.id">
          <td>{{ accountName(r.account_id) }}</td>
          <td>{{ typeName(r.type) }}</td>
          <td>{{ r.threshold }} {{ r.type === 1 ? '%' : '账户币种' }}</td>
          <td>{{ r.enabled ? '✅ 启用' : '⛔ 停用' }}</td>
          <td><button class="btn btn-ghost" @click="toggle(r)">{{ r.enabled ? '停用' : '启用' }}</button><button class="btn btn-del" @click="del(r.id)">删除</button></td>
        </tr>
      </table>
      <p v-else class="hint">还没有规则</p>
    </div>

    <div class="card">
      <h3>告警事件</h3>
      <p v-if="!events.length" class="hint">暂无告警</p>
      <ul class="events">
        <li v-for="e in events" :key="e.id" :class="{ unread: !e.read }">
          <b>{{ kindName(e.kind) }}</b> — {{ e.message }}
          <small>{{ new Date(e.triggered_at).toLocaleString() }}</small>
          <button v-if="!e.read" class="btn btn-ghost" @click="read(e)">标为已读</button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api, errorMessage } from '../lib/api'

const accounts = ref([])
const rules = ref([])
const events = ref([])
const loading = ref(false)
const error = ref('')
const form = ref({ account_id: '', type: 0, threshold: null })

const typeName = (t) => ['余额阈值', '配额阈值', '速率异常'][t] || t
const kindName = (t) => ['余额', '配额', '速率', '采集失败'][t] ?? t
const accountName = (id) => accounts.value.find((a) => a.id === id)?.name ?? `#${id}`

async function refresh() {
  const [a, r, e] = await Promise.all([
    api.get('/accounts'), api.get('/alerts/rules'), api.get('/alerts/events'),
  ])
  accounts.value = a.data
  rules.value = r.data
  events.value = e.data
}

async function add() {
  loading.value = true
  try {
    await api.post('/alerts/rules', form.value)
    form.value = { account_id: '', type: 0, threshold: null }
    await refresh()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function del(id) {
  if (!confirm('删除规则及其历史告警？')) return
  try { await api.delete(`/alerts/rules/${id}`); await refresh() }
  catch (e) { error.value = errorMessage(e) }
}
async function toggle(rule) {
  try { await api.patch(`/alerts/rules/${rule.id}`, { enabled: rule.enabled ? 0 : 1 }); await refresh() }
  catch (e) { error.value = errorMessage(e) }
}
async function read(event) {
  try { await api.patch(`/alerts/events/${event.id}/read`); event.read = true }
  catch (e) { error.value = errorMessage(e) }
}

onMounted(() => refresh().catch(e => { error.value = errorMessage(e) }))
</script>

<style scoped>
.form-row { display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
.tbl { width: 100%; border-collapse: collapse; margin-top: 8px; }
.tbl th, .tbl td { text-align: left; padding: 8px 6px; border-bottom: 1px solid #eee; font-size: 14px; }
.btn-del { background: #e05252; padding: 4px 10px; font-size: 12px; }
.hint { color: #999; font-size: 13px; margin-top: 8px; }
.events { list-style: none; padding: 0; }
.events li { padding: 10px 4px; border-bottom: 1px solid #f0f0f0; display: flex; flex-wrap: wrap; gap: 10px; align-items: baseline; }
.events small { color: #999; margin-left: auto; }
.unread { background: #fff8e6; }
</style>
