import test from 'node:test'
import assert from 'node:assert/strict'
import { estimateCost } from '../src/lib/calculator.js'

test('30 天成本与订阅价差', () => {
  assert.deepEqual(estimateCost({ inputTokens: 1000000, outputTokens: 500000, inputPrice: 2, outputPrice: 4, subscription: 100 }), { api: 120, subscription: 100, difference: 20 })
})
test('无效或缺失价格不生成建议', () => {
  for (const inputPrice of ['', -1, NaN, Infinity]) {
    assert.equal(estimateCost({ inputTokens: 1, outputTokens: 1, inputPrice, outputPrice: 2, subscription: 3 }), null)
  }
})
