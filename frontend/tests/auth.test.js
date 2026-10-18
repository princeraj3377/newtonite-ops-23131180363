import assert from 'node:assert/strict'
import { beforeEach, test } from 'node:test'
import { AxiosError } from 'axios'
import { api, clearSession, getErrorMessage, getToken, signIn, subscribeToSessionExpiry } from '../src/lib/api.js'

const profile = { id: 1, name: 'Test User', email: 'test@example.com' }
let storage

beforeEach(() => {
  storage = new Map()
  globalThis.window = { sessionStorage: {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: (key) => storage.delete(key),
  } }
  clearSession()
})

function response(config, data) {
  return { config, data, status: 200, statusText: 'OK', headers: {} }
}

function reject(config, status) {
  throw new AxiosError('Request failed', 'ERR_BAD_RESPONSE', config, {}, {
    config, status, data: { detail: 'Error' }, headers: {}, statusText: 'Error',
  })
}

function successfulLogin() {
  api.defaults.adapter = async (config) => response(config,
    config.url === '/login' ? { access_token: 'test-token' } : profile)
  return signIn(profile.email, 'test-password')
}

test('login sends JSON credentials, verifies profile, then attaches the saved bearer token', async () => {
  const requests = []
  api.defaults.adapter = async (config) => {
    requests.push(config)
    if (config.url === '/login') {
      assert.equal(config.headers.get('Authorization'), undefined)
      assert.deepEqual(JSON.parse(config.data), { email: profile.email, password: 'test-password' })
      return response(config, { access_token: 'test-token', token_type: 'bearer' })
    }
    assert.equal(config.headers.get('Authorization'), 'Bearer test-token')
    if (requests.length === 2) assert.equal(getToken(), null)
    return response(config, profile)
  }
  assert.deepEqual(await signIn(profile.email, 'test-password'), profile)
  assert.equal(getToken(), 'test-token')
  await api.get('/me')
  assert.deepEqual(requests.map((request) => request.url), ['/login', '/me', '/me'])
  assert.equal(storage.size, 1)
  clearSession()
  assert.equal(getToken(), null)
  assert.equal(storage.size, 0)
})

test('invalid credentials do not save a session', async () => {
  api.defaults.adapter = async (config) => reject(config, 401)
  await assert.rejects(signIn(profile.email, 'wrong'), (error) => {
    assert.match(getErrorMessage(error, 'login'), /Incorrect email or password/)
    return true
  })
  assert.equal(getToken(), null)
})

test('profile failure does not persist a partially authenticated session', async () => {
  api.defaults.adapter = async (config) => config.url === '/login'
    ? response(config, { access_token: 'test-token' }) : reject(config, 503)
  await assert.rejects(signIn(profile.email, 'test-password'))
  assert.equal(getToken(), null)
})

test('malformed login responses never create a session', async () => {
  api.defaults.adapter = async (config) => response(config, {})
  await assert.rejects(signIn(profile.email, 'test-password'), /invalid sign-in response/)
  assert.equal(getToken(), null)
})

test('authenticated 401 clears the session and notifies the UI', async () => {
  await successfulLogin()
  let notified = false
  const unsubscribe = subscribeToSessionExpiry(() => { notified = true })
  try {
    api.defaults.adapter = async (config) => reject(config, 401)
    await assert.rejects(api.get('/me'))
    assert.equal(getToken(), null)
    assert.equal(notified, true)
  } finally {
    unsubscribe()
  }
})

test('server errors and permission denials preserve the existing session', async () => {
  await successfulLogin()
  for (const status of [403, 503]) {
    api.defaults.adapter = async (config) => reject(config, status)
    await assert.rejects(api.get('/me'))
    assert.equal(getToken(), 'test-token')
  }
})

test('a 401 from an old token cannot clear the current session', async () => {
  await successfulLogin()
  api.defaults.adapter = async (config) => reject(config, 401)
  await assert.rejects(api.get('/me', { headers: { Authorization: 'Bearer old-token' } }))
  assert.equal(getToken(), 'test-token')
})

test('existing browser sessions attach their token after a reload', async () => {
  storage.set('newtonite.access_token', 'restored-token')
  api.defaults.adapter = async (config) => {
    assert.equal(config.headers.get('Authorization'), 'Bearer restored-token')
    return response(config, profile)
  }
  assert.deepEqual((await api.get('/me')).data, profile)
})

test('blocked browser storage falls back to an in-memory session', async () => {
  Object.defineProperty(window, 'sessionStorage', { get() { throw new Error('Storage blocked') } })
  await successfulLogin()
  assert.equal(getToken(), 'test-token')
  clearSession()
  assert.equal(getToken(), null)
})

test('network, timeout and validation failures have useful messages', () => {
  assert.match(getErrorMessage(new AxiosError('Network error', 'ERR_NETWORK')), /Unable to connect/)
  assert.match(getErrorMessage(new AxiosError('Timeout', 'ECONNABORTED')), /too long/)
  assert.match(getErrorMessage({ response: { status: 422, data: { detail: [] } } }, 'login'), /check your email/)
})
