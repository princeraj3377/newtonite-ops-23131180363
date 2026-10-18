import axios from 'axios'

const TOKEN_KEY = 'newtonite.access_token'
const expiryListeners = new Set()
let memoryToken = null

export function getToken() {
  try {
    return window.sessionStorage.getItem(TOKEN_KEY) || memoryToken
  } catch {
    return memoryToken
  }
}

function saveToken(token) {
  memoryToken = token
  try {
    window.sessionStorage.setItem(TOKEN_KEY, token)
  } catch {
    // Sign-in still works in memory when browser storage is unavailable.
  }
}

export function clearSession() {
  memoryToken = null
  try {
    window.sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage can be disabled by browser privacy settings.
  }
}

export function subscribeToSessionExpiry(listener) {
  expiryListeners.add(listener)
  return () => expiryListeners.delete(listener)
}

export const api = axios.create({
  baseURL: import.meta.env?.VITE_API_BASE_URL || '/api',
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token && config.authenticated !== false && !config.headers.has('Authorization')) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

api.interceptors.response.use((response) => response, (error) => {
  const token = getToken()
  if (error.response?.status === 401 && token && error.config?.headers?.get('Authorization') === `Bearer ${token}`) {
    clearSession()
    expiryListeners.forEach((listener) => listener())
  }
  return Promise.reject(error)
})

export async function signIn(email, password) {
  const { data } = await api.post('/login', { email, password }, { authenticated: false })
  if (typeof data?.access_token !== 'string' || !data.access_token) {
    throw new Error('The server returned an invalid sign-in response. Please try again.')
  }
  // Only persist a session after the backend confirms the user's identity.
  const { data: profile } = await api.get('/me', {
    authenticated: false,
    headers: { Authorization: `Bearer ${data.access_token}` },
  })
  saveToken(data.access_token)
  return profile
}

export function getErrorMessage(error, context) {
  if (error.code === 'ECONNABORTED') return 'The server took too long to respond. Please try again.'
  if (error.isAxiosError && !error.response) return 'Unable to connect. Check your connection and make sure the API server is running.'
  const status = error.response?.status
  if (status === 401) return context === 'login' ? 'Incorrect email or password. Please try again.' : 'Your session has expired. Please sign in again.'
  if (status >= 500) return 'The server is unavailable right now. Please try again shortly.'
  if (status === 422) return context === 'login' ? 'Please check your email and password and try again.' : 'Please check the form fields and filter values and try again.'
  if (status === 429) return 'Too many attempts. Please wait a moment before trying again.'
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  return error.isAxiosError ? 'Something went wrong. Please try again.' : error.message || 'Something went wrong. Please try again.'
}
