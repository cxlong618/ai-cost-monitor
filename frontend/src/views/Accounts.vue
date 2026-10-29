<template>
  <div>
    <div class="page-head">
      <h2>账户管理</h2>
    </div>

    <div class="card">
      <h3>添加账户</h3>
      <p class="sub">接入厂商后自动采集余额/配额，或选择手动录入模式</p>
      <form @submit.prevent="add" class="form-row">
        <select v-model="form.provider" required>
          <option value="" disabled>选择厂商</option>
          <option v-for="p in providers" :key="p" :value="p">{{ providerName(p) }}</option>
        </select>
        <input v-model="form.name" placeholder="账户别名，如「主力号」" required style="flex:1" />
        <button class="btn" :disabled="loading">{{ loading ? '添加中…' : '+ 添加' }}</button>
      </form>
    </div>

    <div class="card" v-for="a in accounts" :key="a.id">
      <div class="acc-head">
        <div class="acc-title">
          <span class="provider-dot" :class="a.provider"></span>
          <h3>{{ a.name }}</h3>
          <span class="badge badge-gray">{{ providerName(a.provider) }}</span>
          <span class="badge" :class="a.mode === 0 ? 'badge-blue' : 'badge-amber'">
            {{ a.mode === 0 ? '本地 Key 自动采集' : '手动录入' }}
          </span>
        </div>
      </div>

      <div v-if="a.mode === 0" class="key-zone">
        <template v-if="a.keyStored">
          <span class="badge badge-green">🔐 Key 已存本地浏览器</span>
          <button class="btn btn-ghost" @click="collectNow(a)">立即采集</button>
        </template>
        <template v-else>
          <input v-model="keyInput[a.id]" placeholder="粘贴 API Key — 只存你的浏览器，不上传服务器" style="flex:1" />
          <button class="btn" @click="saveLocalKey(a.id)">存入本地</button>
        </template>
      </div>
      <div v-else class="manual-zone">
        <input v-model="manualInput[a.id]" placeholder="粘贴控制台读数，如「余额 9.55 元，已用 40%」" style="flex:1" />
        <button class="btn" @click="saveManual(a.id)">记录快照</button>
      </div>
    </div>

    <div class="card empty-card" v-if="!accounts.length">
      <p class="hint" style="text-align:center">还没有账户，先在上方添加一个</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api, collectAccount } from '../lib/api'
import { saveKey, hasKey } from '../lib/keyStore'

const providers = ref([])
const accounts = ref([])
const keyInput = ref({})
const manualInput = ref({})
const form = ref({ provider: '', name: '' })
const loading = ref(false)

const NAMES = {
  deepseek: 'DeepSeek', zai: '智谱 GLM', openrouter: 'OpenRouter',
  anthropic: 'Anthropic Claude', openai: 'OpenAI', siliconflow: '硅基流动',
}
const providerName = (p) => NAMES[p] || p

async function refresh() {
  const [p, a] = await Promise.all([
    api.get('/accounts/meta/providers'),
    api.get('/accounts'),
  ])
  providers.value = p.data.providers
  if (!form.value.provider) form.value.provider = p.data.providers[0]
  accounts.value = await Promise.all(a.data.map(async (acc) => ({
    ...acc,
    keyStored: acc.mode === 0 ? await hasKey(acc.id) : false,
  })))
}

async function add() {
  loading.value = true
  try {
    await api.post('/accounts', { ...form.value, mode: 1 })
    form.value.name = ''
    await refresh()
  } finally {
    loading.value = false
  }
}

async function saveLocalKey(accountId) {
  const key = keyInput.value[accountId]?.trim()
  if (!key) return alert('请先粘贴 Key')
  await saveKey(accountId, key, 'session')
  keyInput.value[accountId] = ''
  await refresh()
}

async function collectNow(a) {
  try {
    await collectAccount(a.id, 'session')
    alert('采集成功')
  } catch {
    alert('采集失败，请检查 Key 是否有效')
  }
}

async function saveManual(accountId) {
  const text = manualInput.value[accountId]?.trim()
  if (!text) return alert('请粘贴或输入读数')
  try {
    await api.post(`/snapshots/manual?account_id=${accountId}`, { raw_text: text })
    manualInput.value[accountId] = ''
    alert('已记录')
  } catch (e) {
    alert(e.response?.data?.detail || '录入失败')
  }
}

onMounted(refresh)
</script>

<style scoped>
.page-head { margin-bottom: 18px; }
.page-head h2 { font-size: 20px; }
.form-row { display: flex; gap: 10px; margin-top: 14px; }
.acc-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.acc-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.provider-dot { width: 10px; height: 10px; border-radius: 3px; }
.provider-dot.deepseek { background: #4d6bfe; }
.provider-dot.zai { background: #3859ff; }
.provider-dot.openrouter { background: #8b5cf6; }
.provider-dot.anthropic { background: #d97757; }
.provider-dot.openai { background: #10a37f; }
.provider-dot.siliconflow { background: #6366f1; }
.key-zone, .manual-zone { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.empty-card { padding: 40px; }
</style>
