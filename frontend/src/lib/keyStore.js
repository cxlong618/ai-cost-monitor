/**
 * 本地 Key 保险箱 — IndexedDB + WebCrypto
 *
 * 铁律：API Key 只存在用户浏览器里，加密后落 IndexedDB，
 * 请求时随请求头携带，任何情况下不上传到服务器存储。
 */
const DB_NAME = 'acm-keyvault'
const STORE = 'keys'

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE, { keyPath: 'accountId' })
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

/** 加密密钥由登录会话派生（PBKDF2），密钥材料本身不落盘 */
async function deriveCryptoKey(passphrase) {
  const enc = new TextEncoder()
  const baseKey = await crypto.subtle.importKey(
    'raw', enc.encode(passphrase), 'PBKDF2', false, ['deriveKey'],
  )
  // salt 固定于本库（浏览器本地），加密强度依赖用户会话口令
  const salt = enc.encode('acm-keyvault-salt-v1')
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: 310000, hash: 'SHA-256' },
    baseKey,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  )
}

async function put(accountId, record) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).put(record)
    tx.oncomplete = resolve
    tx.onerror = () => reject(tx.error)
  })
}

async function get(accountId) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly')
    const req = tx.objectStore(STORE).get(accountId)
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

/** 保存某账户的 API Key（AES-GCM 加密后存 IndexedDB） */
export async function saveKey(accountId, apiKey, passphrase) {
  const key = await deriveCryptoKey(passphrase)
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const cipher = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv },
    key,
    new TextEncoder().encode(apiKey),
  )
  await put(accountId, {
    accountId,
    iv: Array.from(iv),
    cipher: Array.from(new Uint8Array(cipher)),
    savedAt: Date.now(),
  })
}

/** 取出某账户的明文 Key（仅在发起采集请求的瞬间解密） */
export async function loadKey(accountId, passphrase) {
  const record = await get(accountId)
  if (!record) return null
  const key = await deriveCryptoKey(passphrase)
  try {
    const plain = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: new Uint8Array(record.iv) },
      key,
      new Uint8Array(record.cipher),
    )
    return new TextDecoder().decode(plain)
  } catch {
    return null // 口令不对或数据损坏
  }
}

/** 删除某账户 Key（用户删账户时联动） */
export async function removeKey(accountId) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).delete(accountId)
    tx.oncomplete = resolve
    tx.onerror = () => reject(tx.error)
  })
}

export async function hasKey(accountId) {
  return (await get(accountId)) != null
}
