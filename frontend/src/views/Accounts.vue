<template>
  <div>
    <div class="page-head">
      <h2>账户管理</h2>
    </div>

    <div class="card">
      <h3>本地 Key 保险箱</h3>
      <p class="sub">口令至少 8 位，每次打开页面重新解锁。遗忘后需删除记录并重新录入 Key；旧版本 Key 需重新录入。</p>
      <div class="form-row">
        <input v-model="vaultPassword" type="password" autocomplete="off" placeholder="保险箱口令" />
        <button class="btn" @click="unlock">设置 / 解锁</button>
        <button class="btn btn-ghost" @click="lock">锁定</button>
        <span>{{ unlocked ? '当前页面已解锁' : '已锁定' }}</span>
      </div>
    </div>
    <p v-if="error" role="alert">{{ error }}</p>
    <div class="card">
      <h3>添加账户</h3>
      <p class="sub">接入厂商后自动采集余额/配额，或选择手动录入模式</p>
      <form @submit.prevent="add" class="form-row">
        <select v-model="form.provider" required>
          <option value="" disabled>选择厂商</option>
          <option v-for="p in providers" :key="p" :value="p">{{ providerName(p) }}</option>
        </select>
        <input v-model="form.name" placeholder="账户别名，如「主力号」" required style="flex:1" />
        <select v-model.number="form.mode"><option :value="1">手动录入</option><option :value="0">本地 Key</option></select>
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

      <div class="form-row">
        <input v-model="a.name" maxlength="100" aria-label="账户别名" />
        <button class="btn btn-ghost" @click="rename(a)">保存别名</button>
        <button class="btn btn-ghost" @click="remove(a)">删除账户</button>
      </div>
      <div v-if="a.mode === 0" class="key-zone">
        <template v-if="a.keyStored">
          <span class="badge badge-green">🔐 Key 已存本地浏览器</span>
          <button class="btn btn-ghost" @click="collectNow(a)">立即采集</button>
          <button class="btn btn-ghost" @click="forget(a.id)">删除本地 Key</button>
        </template>
        <template v-else>
          <input v-model="keyInput[a.id]" type="password" autocomplete="off" placeholder="API Key 加密存本地，采集时后端中转" style="flex:1" />
          <button class="btn" @click="saveLocalKey(a.id)">存入本地</button>
        </template>
        <template v-if="a.keyStored">
          <input v-model="keyInput[a.id]" type="password" autocomplete="off" placeholder="输入新 Key 替换已有记录" />
          <button class="btn btn-ghost" @click="saveLocalKey(a.id)">更新 Key</button>
        </template>
        <p v-if="['openai','anthropic'].includes(a.provider)" class="hint">需组织管理员 Admin Key；这两家适配器仍待真实验证。</p>
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
import { api, collectAccount, errorMessage } from '../lib/api'
import { saveKey, hasKey, removeKey, unlockVault, lockVault, vaultUnlocked } from '../lib/keyStore'

const providers = ref([])
const accounts = ref([])
const keyInput = ref({})
const manualInput = ref({})
const form = ref({ provider: '', name: '', mode: 1 })
const loading = ref(false)
const error = ref('')
const vaultPassword = ref('')
const unlocked = ref(vaultUnlocked())
function unlock() {
  try { unlockVault(vaultPassword.value); unlocked.value = true; error.value = '' }
  catch (e) { error.value = errorMessage(e) }
  vaultPassword.value = ''
}
function lock() { lockVault(); unlocked.value = false }
async function rename(a) {
  try { await api.patch(`/accounts/${a.id}`, { name: a.name }); await refresh() }
  catch (e) { error.value = errorMessage(e) }
}
async function forget(id) {
  try { await removeKey(id); await refresh() } catch (e) { error.value = errorMessage(e) }
}
async function remove(a) {
  if (!confirm(`删除账户「${a.name}」？历史数据将保留，但不再显示。`)) return
  try { await api.delete(`/accounts/${a.id}`); await removeKey(a.id); await refresh() }
  catch (e) { error.value = errorMessage(e); await refresh() }
}

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
    await api.post('/accounts', form.value)
    form.value.name = ''
    await refresh()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function saveLocalKey(accountId) {
  const key = keyInput.value[accountId]?.trim()
  if (!key) return alert('请先粘贴 Key')
  try {
    await saveKey(accountId, key)
    keyInput.value[accountId] = ''
    await refresh()
  } catch (e) { error.value = errorMessage(e) }
}

async function collectNow(a) {
  try {
    await collectAccount(a.id)
    alert('采集成功')
  } catch (e) {
    error.value = errorMessage(e)
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
    error.value = errorMessage(e)
  }
}

onMounted(() => refresh().catch(e => { error.value = errorMessage(e) }))
</script>

<style scoped>
.page-head { margin-bottom: 18px; }
.page-head h2 { font-size: 20px; }
.form-row { display: flex; flex-wrap: wrap; gap: 10px; margin: 14px 0; }
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
