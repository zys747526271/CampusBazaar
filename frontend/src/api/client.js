import axios from 'axios'

const USER_TOKEN_KEY = 'cb_token'
const ADMIN_TOKEN_KEY = 'cb_admin_token'

export const tokenStore = {
  user: () => localStorage.getItem(USER_TOKEN_KEY) || '',
  setUser: (token) => {
    if (token) localStorage.setItem(USER_TOKEN_KEY, token)
    else localStorage.removeItem(USER_TOKEN_KEY)
  },
  admin: () => localStorage.getItem(ADMIN_TOKEN_KEY) || '',
  setAdmin: (token) => {
    if (token) localStorage.setItem(ADMIN_TOKEN_KEY, token)
    else localStorage.removeItem(ADMIN_TOKEN_KEY)
  }
}

let authFailureHandler = null
/** 401 统一处理：由 main.js 注册（清登录态 + 跳对应登录页）。403 不触发。 */
export const setAuthFailureHandler = (fn) => {
  authFailureHandler = fn
}

const normalizeError = (error) => {
  const response = error.response
  const payload = response?.data
  const message =
    payload?.message ||
    (error.code === 'ECONNABORTED' ? '请求超时，请检查网络后重试' : '网络异常，请稍后重试')
  const normalized = new Error(message)
  normalized.status = response?.status || 0
  normalized.code = payload?.code || 'NETWORK_ERROR'
  normalized.details = payload?.data
  normalized.requestId = payload?.request_id || response?.headers?.['x-request-id'] || ''
  return normalized
}

function createClient(scope) {
  const isAdmin = scope === 'admin'
  const instance = axios.create({ baseURL: '/api', timeout: 20000 })

  instance.interceptors.request.use((config) => {
    const token = isAdmin ? tokenStore.admin() : tokenStore.user()
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  })

  instance.interceptors.response.use(
    (response) => response.data,
    (error) => {
      const normalized = normalizeError(error)
      // 只有 401 才视为登录态失效；403 表示"已登录但无权限"，仅提示（PRD 7.3）
      if (normalized.status === 401) {
        if (isAdmin) tokenStore.setAdmin('')
        else tokenStore.setUser('')
        if (authFailureHandler) authFailureHandler(scope, normalized)
      }
      return Promise.reject(normalized)
    }
  )
  return instance
}

export const http = createClient('user')
export const adminHttp = createClient('admin')

async function call(instance, method, url, options = {}) {
  const { params, data, headers, responseType, timeout } = options
  const response = await instance.request({ method, url, params, data, headers, responseType, timeout })
  if (responseType === 'blob') return response
  return response?.data
}

const build = (instance) => ({
  get: (url, options) => call(instance, 'get', url, options),
  post: (url, data, options = {}) => call(instance, 'post', url, { ...options, data }),
  put: (url, data, options = {}) => call(instance, 'put', url, { ...options, data }),
  del: (url, options) => call(instance, 'delete', url, options),
  download: (url, options = {}) => call(instance, 'get', url, { ...options, responseType: 'blob' })
})

export const api = build(http)
export const adminApi = build(adminHttp)

/** 图片完整地址（开发态由 Vite 代理 /static 到后端） */
export const imageUrl = (url) => url || ''

export const saveBlob = (blob, filename) => {
  const link = document.createElement('a')
  const objectUrl = URL.createObjectURL(blob)
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 2000)
}
