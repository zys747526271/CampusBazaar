import axios from 'axios'

// 统一 API 实例：请求拦截附带 token；响应拦截返回后端完整对象 {success, message, data}
// 各页面按 response.success / response.data 使用（与原有约定保持一致）
const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) config.headers['Authorization'] = `Bearer ${token}`
    return config
  },
  error => Promise.reject(error)
)

// 双身份令牌分离：普通用户与管理员各用独立的 localStorage 键，避免互相覆盖。
// 后端语义：401 = 未认证/令牌失效（需重新登录）；403 = 已认证但角色不符（不得清除登录态）。
export const TOKEN_KEYS = {
  user: 'token',
  admin: 'admin_token',
  userInfo: 'userInfo',
  adminInfo: 'adminInfo'
}

function clearSession(key) {
  if (key === TOKEN_KEYS.admin) {
    localStorage.removeItem(TOKEN_KEYS.admin)
    localStorage.removeItem(TOKEN_KEYS.adminInfo)
  } else {
    localStorage.removeItem(TOKEN_KEYS.user)
    localStorage.removeItem(TOKEN_KEYS.userInfo)
  }
}

api.interceptors.response.use(
  response => response.data,
  error => {
    const status = error.response?.status
    if (status === 401) {
      const requestUrl = error.config?.url || ''
      const key = requestUrl.startsWith('/admin/') ? TOKEN_KEYS.admin : TOKEN_KEYS.user
      const hadToken = !!localStorage.getItem(key)
      clearSession(key)
      // 只有确实持有该身份令牌时才跳转：避免匿名访问登录接口失败也被踢走
      if (hadToken && location.pathname !== '/auth/login' && location.pathname !== '/admin/login') {
        const target = key === TOKEN_KEYS.admin ? '/admin/login' : '/auth/login'
        location.href = `${target}?redirect=${encodeURIComponent(location.pathname + location.search)}`
      }
    }
    return Promise.reject(error)
  }
)

export default {
  // 通用方法（Dashboard 等直接按路径调用）
  get: (url, config) => api.get(url, config),
  post: (url, data) => api.post(url, data),
  put: (url, data) => api.put(url, data),
  delete: (url, config) => api.delete(url, config),
  auth: {
    captcha: data => api.post('/auth/captcha', data),
    register: data => api.post('/auth/register', data),
    login: data => api.post('/auth/login', data),
    adminLogin: data => api.post('/auth/admin/login', data),
    adminRegister: data => api.post('/auth/admin/register', data),
    getProfile: () => api.get('/auth/profile'),
    updateProfile: data => api.put('/auth/profile', data),
    changePassword: data => api.put('/users/password', data)
  },
  products: {
    getList: params => api.get('/products', { params }),
    getDetail: id => api.get(`/products/${id}`),
    create: data => api.post('/products', data),
    update: (id, data) => api.put(`/products/${id}`, data),
    remove: id => api.delete(`/products/${id}`),
    delete: id => api.delete(`/products/${id}`),
    uploadImage: (id, formData) => api.post(`/products/${id}/images`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    getRecommended: () => api.get('/products/recommended'),
    getHot: () => api.get('/products/hot')
  },
  cart: {
    getItems: () => api.get('/carts/cart'),
    addItem: data => api.post('/carts/cart', data),
    updateItem: (id, data) => api.put(`/carts/${id}`, data),
    removeItem: id => api.delete(`/carts/${id}`),
    batchRemove: ids => api.delete('/carts/batch', { data: { cart_ids: ids } })
  },
  orders: {
    getList: params => api.get('/orders', { params }),
    getDetail: id => api.get(`/orders/${id}`),
    create: data => api.post('/orders', data),
    updateStatus: (id, status) => api.put(`/orders/${id}/status`, { status }),
    remove: id => api.delete(`/orders/${id}`)
  },
  addresses: {
    getList: () => api.get('/addresses'),
    create: data => api.post('/addresses', data),
    update: (id, data) => api.put(`/addresses/${id}`, data),
    remove: id => api.delete(`/addresses/${id}`),
    getDefault: () => api.get('/addresses/default'),
    setDefault: id => api.put(`/addresses/set-default/${id}`),
    getRegions: () => api.get('/addresses/regions')
  },
  tags: {
    getList: params => api.get('/tags', { params }),
    getDetail: id => api.get(`/tags/${id}`)
  },
  comments: {
    getByProduct: (id, params) => api.get(`/comments/product/${id}`, { params }),
    create: data => api.post('/comments', data),
    like: id => api.post(`/comments/${id}/like`),
    unlike: id => api.post(`/comments/${id}/unlike`)
  },
  favorites: {
    getList: () => api.get('/favorites'),
    add: productId => api.post(`/favorites/${productId}`),
    remove: productId => api.delete(`/favorites/${productId}`),
    check: productId => api.get(`/favorites/${productId}/check`)
  },
  history: {
    getList: () => api.get('/history'),
    record: productId => api.post(`/history/${productId}`),
    clear: () => api.delete('/history')
  },
  seller: {
    become: () => api.post('/seller/become'),
    myProducts: () => api.get('/seller/products'),
    productComments: id => api.get(`/seller/products/${id}/comments`),
    receivedOrders: () => api.get('/seller/orders'),
    stats: () => api.get('/seller/stats'),
    toggleProduct: id => api.put(`/seller/products/${id}/toggle`),
    categories: () => api.get('/seller/categories'),
    createCategory: data => api.post('/seller/categories', data),
    updateCategory: (id, data) => api.put(`/seller/categories/${id}`, data),
    deleteCategory: id => api.delete(`/seller/categories/${id}`)
  },
  admin: {
    getSellers: params => api.get('/admin/sellers', { params }),
    getSellerProducts: (id, params) => api.get(`/admin/sellers/${id}/products`, { params }),
    getComments: params => api.get('/admin/comments', { params }),
    toggleCommentVisibility: (id, data) => api.put(`/admin/comments/${id}/visibility`, data),    getUsers: params => api.get('/admin/users', { params }),
    getUserDetail: id => api.get(`/admin/users/${id}`),
    banUser: (id, isBanned) => api.put(`/admin/users/${id}/ban`, { is_banned: isBanned }),
    removeUser: id => api.delete(`/admin/users/${id}`),
    deleteUser: id => api.delete(`/admin/users/${id}`),
    getPendingProducts: () => api.get('/admin/products/pending'),
    batchUpdateProductStatus: data => api.put('/admin/products/batch/status', data),
    getUserOrders: userId => api.get(`/admin/users/${userId}/orders`),
    resetUserPassword: userId => api.put(`/admin/users/${userId}/reset_password`),
    updateUser: (userId, data) => api.put(`/admin/users/${userId}`, data)
  }
}
