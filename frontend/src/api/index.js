/** 接口封装：按领域分组，页面不直接写 URL 字符串。 */
import { adminApi, api, imageUrl } from './client'

export { imageUrl, tokenStore, setAuthFailureHandler, saveBlob } from './client'

export const authApi = {
  captcha: (payload) => api.post('/auth/captcha', payload),
  register: (payload) => api.post('/auth/register', payload),
  login: (payload) => api.post('/auth/login', payload),
  logout: () => api.post('/auth/logout'),
  profile: () => api.get('/auth/profile'),
  updateProfile: (payload) => api.put('/auth/profile', payload),
  changePassword: (payload) => api.put('/auth/password', payload),
  resetPassword: (payload) => api.post('/auth/reset-password', payload),
  adminLogin: (payload) => adminApi.post('/auth/admin/login', payload),
  adminRegister: (payload) => adminApi.post('/auth/admin/register', payload),
  adminProfile: () => adminApi.get('/auth/admin/profile')
}

export const catalogApi = {
  home: () => api.get('/meta/home'),
  filters: () => api.get('/meta/filters'),
  options: () => api.get('/meta/options'),
  products: (params) => api.get('/products', { params }),
  product: (id) => api.get(`/products/${id}`),
  related: (id) => api.get(`/products/${id}/related`),
  comments: (id, params) => api.get(`/products/${id}/comments`, { params }),
  tags: () => api.get('/tags'),
  shop: (id) => api.get(`/shops/${id}`),
  shopProducts: (id, params) => api.get(`/shops/${id}/products`, { params }),
  suggest: (keyword) => api.get('/search/suggest', { params: { keyword } })
}

export const cartApi = {
  list: () => api.get('/carts'),
  count: () => api.get('/carts/count'),
  add: (payload) => api.post('/carts', payload),
  update: (id, payload) => api.put(`/carts/${id}`, payload),
  remove: (id) => api.del(`/carts/${id}`),
  clear: (mode = 'all') => api.del('/carts', { params: { mode } }),
  batch: (payload) => api.post('/carts/batch', payload),
  selectAll: (selected) => api.put('/carts/select-all', { selected }),
  checkout: () => api.get('/carts/checkout')
}

export const orderApi = {
  preview: (payload) => api.post('/orders/preview', payload),
  create: (payload) => api.post('/orders', payload, { headers: { 'Idempotency-Key': newKey() } }),
  list: (params) => api.get('/orders', { params }),
  counts: () => api.get('/orders/counts'),
  detail: (id) => api.get(`/orders/${id}`),
  pay: (id) => api.post(`/orders/${id}/pay`),
  cancel: (id, reason) => api.post(`/orders/${id}/cancel`, { reason }),
  confirm: (id) => api.post(`/orders/${id}/confirm`),
  refund: (id, reason) => api.post(`/orders/${id}/refund`, { reason }),
  cancelRefund: (id) => api.post(`/orders/${id}/cancel-refund`)
}

export const favoriteApi = {
  list: (params) => api.get('/favorites', { params }),
  add: (productId) => api.post('/favorites', { product_id: productId }),
  remove: (productId) => api.del(`/favorites/${productId}`)
}

export const historyApi = {
  list: (params) => api.get('/history', { params }),
  clear: () => api.del('/history')
}

export const commentApi = {
  create: (payload) => api.post('/comments', payload),
  mine: (params) => api.get('/comments/mine', { params }),
  like: (id) => api.post(`/comments/${id}/like`),
  remove: (id) => api.del(`/comments/${id}`),
  report: (payload) => api.post('/reports', payload)
}

export const messageApi = {
  list: (params) => api.get('/messages', { params }),
  unread: () => api.get('/messages/unread'),
  read: (id) => api.post(`/messages/${id}/read`),
  readAll: () => api.post('/messages/read-all'),
  remove: (id) => api.del(`/messages/${id}`)
}

export const addressApi = {
  list: () => api.get('/addresses'),
  create: (payload) => api.post('/addresses', payload),
  update: (id, payload) => api.put(`/addresses/${id}`, payload),
  remove: (id) => api.del(`/addresses/${id}`),
  setDefault: (id) => api.put(`/addresses/${id}/default`)
}

export const balanceApi = {
  info: () => api.get('/balance'),
  logs: (params) => api.get('/balance/logs', { params }),
  recharge: (amount) => api.post('/balance/recharge', { amount })
}

export const uploadApi = {
  image: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/uploads/image', form)
  }
}

export const sellerApi = {
  become: () => api.post('/seller/become'),
  overview: () => api.get('/seller/overview'),
  products: (params) => api.get('/seller/products', { params }),
  product: (id) => api.get(`/seller/products/${id}`),
  createProduct: (payload) => api.post('/seller/products', payload),
  updateProduct: (id, payload) => api.put(`/seller/products/${id}`, payload),
  toggleProduct: (id) => api.post(`/seller/products/${id}/toggle`),
  deleteProduct: (id) => api.del(`/seller/products/${id}`),
  orders: (params) => api.get('/seller/orders', { params }),
  ship: (id, payload) => api.post(`/seller/orders/${id}/ship`, payload),
  confirmPaid: (id) => api.post(`/seller/orders/${id}/confirm-paid`),
  closeOrder: (id, reason) => api.post(`/seller/orders/${id}/close`, { reason }),
  handleRefund: (id, payload) => api.post(`/seller/orders/${id}/refund`, payload),
  categories: () => api.get('/seller/categories'),
  createCategory: (payload) => api.post('/seller/categories', payload),
  updateCategory: (id, payload) => api.put(`/seller/categories/${id}`, payload),
  deleteCategory: (id) => api.del(`/seller/categories/${id}`),
  comments: (params) => api.get('/seller/comments', { params }),
  replyComment: (id, reply) => api.post(`/seller/comments/${id}/reply`, { reply })
}

export const adminApiClient = {
  stats: () => adminApi.get('/admin/stats'),
  runJobs: () => adminApi.post('/admin/jobs/run'),

  users: (params) => adminApi.get('/admin/users', { params }),
  user: (id) => adminApi.get(`/admin/users/${id}`),
  banUser: (id, payload) => adminApi.put(`/admin/users/${id}/ban`, payload),
  resetUserPassword: (id, payload = {}) => adminApi.put(`/admin/users/${id}/reset-password`, payload),
  deleteUser: (id) => adminApi.del(`/admin/users/${id}`),
  userOrders: (id, params) => adminApi.get(`/admin/users/${id}/orders`, { params }),
  userProducts: (id, params) => adminApi.get(`/admin/users/${id}/products`, { params }),

  sellers: (params) => adminApi.get('/admin/sellers', { params }),
  sellerProducts: (id, params) => adminApi.get(`/admin/sellers/${id}/products`, { params }),

  products: (params) => adminApi.get('/admin/products', { params }),
  product: (id) => adminApi.get(`/admin/products/${id}`),
  updateProductStatus: (id, payload) => adminApi.put(`/admin/products/${id}/status`, payload),
  batchProductStatus: (payload) => adminApi.post('/admin/products/batch-status', payload),
  featureProduct: (id, featured) => adminApi.put(`/admin/products/${id}/feature`, { featured }),
  productTags: () => adminApi.get('/admin/products/tags'),

  comments: (params) => adminApi.get('/admin/comments', { params }),
  commentVisibility: (id, payload) => adminApi.put(`/admin/comments/${id}/visibility`, payload),
  deleteComment: (id) => adminApi.del(`/admin/comments/${id}`),

  orders: (params) => adminApi.get('/admin/orders', { params }),
  order: (id) => adminApi.get(`/admin/orders/${id}`),
  orderSummary: () => adminApi.get('/admin/orders/summary'),
  cancelOrder: (id, reason) => adminApi.post(`/admin/orders/${id}/cancel`, { reason }),
  refundOrder: (id, payload) => adminApi.post(`/admin/orders/${id}/refund`, payload),

  tags: () => adminApi.get('/admin/tags'),
  createTag: (payload) => adminApi.post('/admin/tags', payload),
  updateTag: (id, payload) => adminApi.put(`/admin/tags/${id}`, payload),
  deleteTag: (id) => adminApi.del(`/admin/tags/${id}`),

  banners: () => adminApi.get('/admin/banners'),
  createBanner: (payload) => adminApi.post('/admin/banners', payload),
  updateBanner: (id, payload) => adminApi.put(`/admin/banners/${id}`, payload),
  deleteBanner: (id) => adminApi.del(`/admin/banners/${id}`),

  reports: (params) => adminApi.get('/admin/reports', { params }),
  handleReport: (id, payload) => adminApi.put(`/admin/reports/${id}`, payload),

  auditLogs: (params) => adminApi.get('/admin/audit-logs', { params }),
  exportCsv: (kind) => adminApi.download(`/admin/export/${kind}`)
}

function newKey() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID()
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}
