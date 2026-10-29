/** v2 保险箱：用户隔离、随机盐、用户口令；口令仅存内存。 */
const DB_NAME = 'acm-keyvault-v2'
let passphrase = ''
export function unlockVault(value) {
  if (!globalThis.isSecureContext || !globalThis.crypto?.subtle) throw new Error('本地 Key 需要 HTTPS 或 localhost 安全环境')
  if (value.length < 8) throw new Error('保险箱口令至少 8 位；遗忘后需重新录入 Key')
  passphrase = value
}
export function lockVault() { passphrase = '' }
export function vaultUnlocked() { return Boolean(passphrase) }
function recordId(accountId) {
  const userId = localStorage.getItem('acm_user_id')
  if (!userId) throw new Error('请重新登录以初始化个人保险箱')
  return `${userId}:${accountId}`
}
function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => req.result.createObjectStore('keys', { keyPath: 'id' })
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}
async function transact(mode, action) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction('keys', mode)
    const req = action(tx.objectStore('keys'))
    tx.oncomplete = () => { db.close(); resolve(req.result) }
    tx.onerror = tx.onabort = () => { db.close(); reject(tx.error || new Error('保险箱访问失败')) }
  })
}
async function deriveKey(salt) {
  if (!passphrase) throw new Error('请先到账户管理解锁本地保险箱')
  const base = await crypto.subtle.importKey('raw', new TextEncoder().encode(passphrase), 'PBKDF2', false, ['deriveKey'])
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: 310000, hash: 'SHA-256' }, base,
    { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt'],
  )
}
export async function saveKey(accountId, apiKey) {
  const id = recordId(accountId)
  if (await transact('readonly', store => store.get(id))) await loadKey(accountId)
  const salt = crypto.getRandomValues(new Uint8Array(16))
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const key = await deriveKey(salt)
  const cipher = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, new TextEncoder().encode(apiKey))
  await transact('readwrite', store => store.put({ id, salt: [...salt], iv: [...iv], cipher: [...new Uint8Array(cipher)] }))
}
export async function loadKey(accountId) {
  const record = await transact('readonly', store => store.get(recordId(accountId)))
  if (!record) return null
  const key = await deriveKey(new Uint8Array(record.salt))
  try {
    const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: new Uint8Array(record.iv) }, key, new Uint8Array(record.cipher))
    return new TextDecoder().decode(plain)
  } catch { throw new Error('保险箱口令不匹配或密文损坏，请重新解锁') }
}
export async function removeKey(accountId) {
  await transact('readwrite', store => store.delete(recordId(accountId)))
}
export async function hasKey(accountId) {
  return Boolean(await transact('readonly', store => store.get(recordId(accountId))))
}
