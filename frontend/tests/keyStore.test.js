import test from 'node:test'
import assert from 'node:assert/strict'
import 'fake-indexeddb/auto'
import { unlockVault, lockVault, vaultUnlocked, saveKey, loadKey, hasKey, removeKey } from '../src/lib/keyStore.js'

const storage = new Map([['acm_user_id', '1']])
globalThis.localStorage = { getItem: key => storage.get(key) }
globalThis.isSecureContext = true

test('密文保险箱：口令、用户隔离、更新和删除', async () => {
  unlockVault('test-vault-passphrase')
  await saveKey(42, 'dummy-key')
  assert.equal(await hasKey(42), true)
  assert.equal(await loadKey(42), 'dummy-key')
  lockVault()
  assert.equal(vaultUnlocked(), false)
  await assert.rejects(loadKey(42), /解锁/)
  unlockVault('wrong-passphrase')
  await assert.rejects(loadKey(42), /口令不匹配/)
  await assert.rejects(saveKey(42, 'replacement'), /口令不匹配/)
  unlockVault('test-vault-passphrase')
  assert.equal(await loadKey(42), 'dummy-key')
  storage.set('acm_user_id', '2')
  assert.equal(await hasKey(42), false)
  assert.equal(await loadKey(42), null)
  storage.set('acm_user_id', '1')
  await saveKey(42, 'new-dummy-key')
  assert.equal(await loadKey(42), 'new-dummy-key')
  await removeKey(42)
  assert.equal(await hasKey(42), false)
  globalThis.isSecureContext = false
  assert.throws(() => unlockVault('test-vault-passphrase'), /HTTPS/)
  globalThis.isSecureContext = true
  assert.throws(() => unlockVault('short'), /8 位/)
  lockVault()
})
