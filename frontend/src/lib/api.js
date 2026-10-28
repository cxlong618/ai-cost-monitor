import axios from 'axios'
import { loadKey } from './keyStore'

export const api = axios.create({ baseURL: '/api' })

/**
 * 打开页面自动采集：从本地保险箱解密 Key → 放请求头 → 后端内存中转
 * Key 只在本次请求的生命周期内存在
 */
export async function collectAccount(accountId, passphrase) {
  const key = await loadKey(accountId, passphrase)
  if (!key) throw new Error('本地无 Key 或口令不匹配')
  return api.post(`/accounts/${accountId}/collect`, null, {
    headers: { 'X-Provider-Key': key },
  })
}
