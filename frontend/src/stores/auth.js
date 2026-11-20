import { defineStore } from 'pinia'
import { authApi, tokenStore } from '@/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: tokenStore.user(),
    adminToken: tokenStore.admin(),
    user: null,
    admin: null,
    profileLoaded: false,
    adminLoaded: false
  }),

  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    isSeller: (state) => Boolean(state.user?.is_seller),
    isAdmin: (state) => Boolean(state.adminToken),
    displayName: (state) => state.user?.nickname || '同学',
    avatar: (state) => state.user?.avatar_url || ''
  },

  actions: {
    setSession({ token, user }) {
      this.token = token || ''
      this.user = user || null
      this.profileLoaded = true
      tokenStore.setUser(this.token)
    },

    async login(payload) {
      const data = await authApi.login(payload)
      this.setSession(data)
      return data
    },

    async register(payload) {
      const data = await authApi.register(payload)
      this.setSession(data)
      return data
    },

    async fetchProfile(force = false) {
      if (!this.token) return null
      if (this.profileLoaded && !force) return this.user
      try {
        this.user = await authApi.profile()
        this.profileLoaded = true
        return this.user
      } catch (error) {
        if (error.status === 401) this.clearUser()
        throw error
      }
    },

    async updateProfile(payload) {
      this.user = await authApi.updateProfile(payload)
      return this.user
    },

    async logout() {
      try {
        if (this.token) await authApi.logout()
      } catch (error) {
        /* 忽略登出接口异常，前端仍然清态 */
      }
      this.clearUser()
    },

    clearUser() {
      this.token = ''
      this.user = null
      this.profileLoaded = false
      tokenStore.setUser('')
    },

    async adminLogin(payload) {
      const data = await authApi.adminLogin(payload)
      this.adminToken = data.token
      this.admin = data.admin
      this.adminLoaded = true
      tokenStore.setAdmin(data.token)
      return data
    },

    async fetchAdmin(force = false) {
      if (!this.adminToken) return null
      if (this.adminLoaded && !force) return this.admin
      this.admin = await authApi.adminProfile()
      this.adminLoaded = true
      return this.admin
    },

    adminLogout() {
      this.adminToken = ''
      this.admin = null
      this.adminLoaded = false
      tokenStore.setAdmin('')
    },

    /** 401 统一处理入口（由 main.js 注册） */
    onUnauthorized(scope) {
      if (scope === 'admin') {
        this.adminToken = ''
        this.admin = null
        this.adminLoaded = false
        tokenStore.setAdmin('')
      } else {
        this.clearUser()
      }
    }
  }
})
