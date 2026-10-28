<template>
  <div>
    <div class="card">
      <h3>添加账户</h3>
      <form @submit.prevent="add" style="display:flex; gap:12px; align-items:center; margin-top:12px;">
        <select v-model="form.provider">
          <option v-for="p in providers" :key="p" :value="p">{{ p }}</option>
        </select>
        <input v-model="form.name" placeholder="账户别名，如「主力号」" required />
        <button class="btn" :disabled="loading">{{ loading ? '添加中…' : '添加' }}</button>
      </form>
    </div>

    <div class="card" v-for="a in accounts" :key="a.id">
      <h3>
        {{ a.name }} <small>{{ a.provider }} · {{ a.mode === 0 ? '本地Key' : '手动录入' }}</small>
      </h3>
      <div v-if="a.mode !== 0" style="margin-top:8px; color:#888; font-size:13px;">
        手动模式：粘贴控制台账单读数即可记录快照（TODO: 一键粘贴解析）
      </div>
      <div v-else style="margin-top:8px; font-size:13px;">
        <span v-if="a.keyStored" style="color:#2a9d4a;">🔐 Key 已存本地</span>
        <template v-else>
          <input v-model="keyInput[a.id]" placeholder="粘贴 API Key（只存你的浏览器）" style="width:280px" />
          <button class="btn" style="margin-left:8px" @click="saveLocalKey(a.id)">存入本地</button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../lib/api'
import { saveKey, hasKey } from '../lib/keyStore'

const providers = ref([])
const accounts = ref([])
const keyInput = ref({})
const form = ref({ provider: '', name: '', mode: 1 })
const loading = ref(false)

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
  // demo 阶段口令用 'session'，接入登录后改为登录会话派生
  await saveKey(accountId, key, 'session')
  keyInput.value[accountId] = ''
  await refresh()
}

onMounted(refresh)
</script>
