import assert from 'node:assert/strict'
import { test } from 'node:test'
import { api, getErrorMessage } from '../src/lib/api.js'
import { createItemSubmission, itemsPath } from '../src/lib/workItems.js'

test('item queries combine filters, trim text and encode special characters', () => {
  const path = itemsPath(42, { q: '  gateway & 100%  ', status: 'open', priority: 'high', item_type: 'payment' })
  const url = new URL(path, 'http://localhost')
  assert.equal(url.pathname, '/items')
  assert.deepEqual(Object.fromEntries(url.searchParams), { team_id: '42', q: 'gateway & 100%', status: 'open', priority: 'high', item_type: 'payment' })
  assert.equal(itemsPath(42, { q: ' ', status: '', priority: '' }), '/items?team_id=42')
})

test('uncertain create retries reuse the key; changed payloads and new forms get new keys', async () => {
  const requests = []
  api.defaults.adapter = async (config) => {
    requests.push(config)
    if (requests.length === 1) throw new Error('Simulated network interruption')
    return { data: { id: 1 }, config, status: 201, statusText: 'Created', headers: {} }
  }
  const submit = createItemSubmission()
  const payload = { team_id: 1, title: 'Test item', description: 'Details', item_type: 'task', priority: 'medium' }
  await assert.rejects(submit(payload))
  await submit(payload)
  await submit({ ...payload, title: 'Updated title' })
  await submit(payload)
  await createItemSubmission()(payload)
  const keys = requests.map((request) => request.headers.get('Idempotency-Key'))
  assert.ok(keys[0])
  assert.equal(keys[0], keys[1])
  assert.notEqual(keys[1], keys[2])
  assert.equal(keys[0], keys[3])
  assert.notEqual(keys[3], keys[4])
  assert.deepEqual(JSON.parse(requests[0].data), payload)
})

test('work item validation errors do not refer to login credentials', () => {
  assert.match(getErrorMessage({ response: { status: 422 } }), /form fields and filter values/)
})
