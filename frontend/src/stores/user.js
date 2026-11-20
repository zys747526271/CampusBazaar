import { defineStore } from 'pinia'
import axios from 'axios'

/**
 * 用户状态：统一在此处理登录态、角色（买家/卖家/管理员）。
 * 注意：所有登录入口都必须走 login()/adminLogin()，直接写 localStorage 会导致
 * 顶部导航读不到最新状态（旧版 LoginPage 的 bug 根因）。
 */
export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: JSON.parse(localStorage.getItem('userInfo') || '{}'),
    adminToken: localStorage.getItem('admin_token') || '',
    adminInfo: JSON.parse(localStorage.getItem('adminInfo') || '{}'),
    isAuthenticated: !!localStorage.getItem('token'),
    isAdminAuthenticated: !!localStorage.getItem('admin_token')
  }),

  getters: {
    // 当前展示身份：管理员令牌存在时优先展示管理员，否则展示普通用户
    isAdmin: (state) => state.isAdminAuthenticated && !state.isAuthenticated,
    isSeller: (state) => state.userInfo.is_seller === true,
    userId: (state) => state.userInfo.id,
    displayName: (state) =>
      (state.isAdminAuthenticated && !state.isAuthenticated
        ? state.adminInfo.username
        : state.userInfo.nickname || state.userInfo.username) || '用户',
    avatar: (state) => state.isAuthenticated
      ? (state.userInfo.avatar_url || state.userInfo.avatar || '')
      : ''
  },

  actions: {
    _persist(token, user) {
      this.token = token
      this.userInfo = user
      this.isAuthenticated = true
      localStorage.setItem('token', token)
      localStorage.setItem('userInfo', JSON.stringify(user))
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    },

    _persistAdmin(token, admin) {
      this.adminToken = token
      this.adminInfo = admin
      this.isAdminAuthenticated = true
      localStorage.setItem('admin_token', token)
      localStorage.setItem('adminInfo', JSON.stringify(admin))
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    },

    async login(credentials) {
      try {
        // 后端返回 { success, message, data: { token, user } }
        const resp = await axios.post('/api/auth/login', credentials)
        const payload = resp.data.data || resp.data
        this._persist(payload.token, { ...payload.user, isAdmin: false })
        return { success: true }
      } catch (error) {
        return {
          success: false,
          message: error.response?.data?.message || '登录失败，请检查手机号和密码'
        }
      }
    },

    async register(userData) {
      try {
        const resp = await axios.post('/api/auth/register', userData)
        return { success: true, data: resp.data.data }
      } catch (error) {
        return { success: false, message: error.response?.data?.message || '注册失败，请稍后再试' }
      }
    },

    async adminLogin(credentials) {
      try {
        const resp = await axios.post('/api/auth/admin/login', credentials)
        const payload = resp.data.data || resp.data
        this._persistAdmin(payload.token, { ...payload.admin, isAdmin: true })
        return { success: true }
      } catch (error) {
        return { success: false, message: error.response?.data?.message || '管理员登录失败' }
      }
    },

    async becomeSeller() {
      try {
        const resp = await axios.post('/api/seller/become')
        if (resp.data.success) {
          this.userInfo = { ...this.userInfo, is_seller: true }
          localStorage.setItem('userInfo', JSON.stringify(this.userInfo))
        }
        return { success: resp.data.success, message: resp.data.message }
      } catch (error) {
        return { success: false, message: error.response?.data?.message || '开通失败' }
      }
    },

    async fetchUserProfile() {
      try {
        const resp = await axios.get('/api/auth/profile')
        const data = resp.data.data || resp.data
        this.userInfo = { ...this.userInfo, ...data }
        localStorage.setItem('userInfo', JSON.stringify(this.userInfo))
        return { success: true, data }
      } catch (error) {
        return { success: false, message: '获取用户信息失败' }
      }
    },

    // 退出当前前台身份；保留管理员令牌，避免管理后台操作被前台退出连带清掉
    logout() {
      if (this.isAdminAuthenticated && !this.isAuthenticated) {
        this.adminToken = ''
        this.adminInfo = {}
        this.isAdminAuthenticated = false
        localStorage.removeItem('admin_token')
        localStorage.removeItem('adminInfo')
      } else {
        this.token = ''
        this.userInfo = {}
        this.isAuthenticated = false
        localStorage.removeItem('token')
        localStorage.removeItem('userInfo')
      }
      delete axios.defaults.headers.common['Authorization']
    },

    adminLogout() {
      this.adminToken = ''
      this.adminInfo = {}
      this.isAdminAuthenticated = false
      localStorage.removeItem('admin_token')
      localStorage.removeItem('adminInfo')
      delete axios.defaults.headers.common['Authorization']
    }
  }
})
