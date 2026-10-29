import axios from 'axios'
import { loadKey, lockVault } from './keyStore'

export const api = axios.create({ baseURL: '/api' })

api.interceptors.response.use(response => response, error => {
  if (error.response?.status === 401 && !error.config?.url?.startsWith('/auth/')) {
    localStorage.removeItem('acm_token')
    localStorage.removeItem('acm_user_id')
    delete api.defaults.headers.common.Authorization
    lockVault()
    location.assign('/login')
  }
  return Promise.reject(error)
})
export function errorMessage(error) {
  const detail = error.response?.data?.detail
  return typeof detail === 'string' ? detail : Array.isArray(detail)
    ? detail.map(item => item.msg).join('；') : error.message || '请求失败'
}

// 恢复登录态
const token = localStorage.getItem('acm_token')
if (token) api.defaults.headers.common['Authorization'] = `Bearer ${token}`

/**
 * 打开页面自动采集：从本地保险箱解密 Key → 放请求头 → 后端内存中转
 * Key 只在本次请求的生命周期内存在
 */
export async function collectAccount(accountId) {
  const key = await loadKey(accountId)
  if (!key) throw new Error('本地无 Key 或口令不匹配')
  return api.post(`/accounts/${accountId}/collect`, null, {
    headers: { 'X-Provider-Key': key },
  })
}
