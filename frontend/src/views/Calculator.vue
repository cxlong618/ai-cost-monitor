<template>
  <div class="card">
    <h3>订阅计算器（免费 · 免登录）</h3>
    <p class="hint">填入厂商当前单价，统一使用同一币种。按每月 30 天估算，不含税费和缓存折扣。</p>
    <form @submit.prevent class="calculator-form">
      <label>币种 <select v-model="currency"><option>CNY</option><option>USD</option></select></label>
      <label>日均输入 token <input v-model.number="form.inputTokens" type="number" min="0" required /></label>
      <label>日均输出 token <input v-model.number="form.outputTokens" type="number" min="0" required /></label>
      <label>输入单价（每百万 token）<input v-model.number="form.inputPrice" type="number" min="0" step="any" required /></label>
      <label>输出单价（每百万 token）<input v-model.number="form.outputPrice" type="number" min="0" step="any" required /></label>
      <label>订阅月费 <input v-model.number="form.subscription" type="number" min="0" step="any" required /></label>
    </form>
    <div v-if="result" aria-live="polite">
      <p>API 月费用估算：<b>{{ currency }} {{ result.api.toFixed(2) }}</b></p>
      <p>订阅月费：{{ currency }} {{ result.subscription.toFixed(2) }}</p>
      <p>{{ result.difference > 0 ? '订阅名义费用较低' : result.difference < 0 ? 'API 名义费用较低' : '名义费用相同' }}，月价差 {{ currency }} {{ Math.abs(result.difference).toFixed(2) }}</p>
    </div>
    <p v-else class="hint">请填写完整且不小于零的用量和价格。</p>
    <p class="hint">订阅与 API 的模型、额度、限流及使用条款可能不同，请核对后决定；此结果不代表订阅一定能覆盖用量。</p>
    <router-link to="/login">登录成本监控</router-link>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { estimateCost } from '../lib/calculator'
const currency = ref('CNY')
const form = ref({ inputTokens: '', outputTokens: '', inputPrice: '', outputPrice: '', subscription: '' })
const result = computed(() => estimateCost(form.value))
</script>
<style scoped>
.calculator-form { display: grid; gap: 14px; margin: 18px 0; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
label { display: flex; flex-direction: column; gap: 6px; }
</style>
