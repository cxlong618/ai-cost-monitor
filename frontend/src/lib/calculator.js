export function estimateCost({ inputTokens, outputTokens, inputPrice, outputPrice, subscription }) {
  const values = [inputTokens, outputTokens, inputPrice, outputPrice, subscription]
  if (values.some(value => typeof value !== 'number' || !Number.isFinite(value) || value < 0)) return null
  const api = 30 * (inputTokens * inputPrice + outputTokens * outputPrice) / 1000000
  if (!Number.isFinite(api)) return null
  return { api, subscription, difference: api - subscription }
}
