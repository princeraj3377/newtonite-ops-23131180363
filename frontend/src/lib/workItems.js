import { api } from './api.js'

export const statuses = ['open', 'in_progress', 'resolved', 'closed']
export const priorities = ['low', 'medium', 'high', 'critical']
export const itemTypes = ['incident', 'customer_issue', 'payment', 'compliance', 'task']
export const transitions = { open: ['in_progress'], in_progress: ['resolved', 'open'], resolved: ['closed', 'in_progress'], closed: [] }
export const label = (value) => value.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase())

export function itemsPath(teamId, filters) {
  const params = new URLSearchParams({ team_id: String(teamId) })
  for (const key of ['q', 'status', 'priority', 'item_type']) {
    const value = filters[key]?.trim()
    if (value) params.set(key, value)
  }
  return `/items?${params}`
}

// Keep the same key when retrying an unchanged submission after a timeout.
export function createItemSubmission() {
  const keys = new Map()
  return async (payload) => {
    const signature = JSON.stringify(payload)
    if (!keys.has(signature)) keys.set(signature, crypto.randomUUID())
    const { data } = await api.post('/items', payload, {
      headers: { 'Idempotency-Key': keys.get(signature) },
    })
    return data
  }
}
