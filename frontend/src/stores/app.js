import { defineStore } from 'pinia'
import { catalogApi, messageApi } from '@/api'
import { useAuthStore } from './auth'

export const useAppStore = defineStore('app', {
  state: () => ({
    tags: [],
    filters: null,
    options: null,
    unread: 0,
    filtersLoaded: false,
    optionsLoaded: false
  }),

  actions: {
    async loadFilters(force = false) {
      if (this.filtersLoaded && !force) return this.filters
      const data = await catalogApi.filters()
      this.filters = data
      this.tags = data.tags || []
      this.filtersLoaded = true
      return data
    },

    async loadOptions(force = false) {
      if (this.optionsLoaded && !force) return this.options
      this.options = await catalogApi.options()
      this.optionsLoaded = true
      return this.options
    },

    async loadUnread() {
      const auth = useAuthStore()
      if (!auth.isLoggedIn) {
        this.unread = 0
        return
      }
      try {
        const data = await messageApi.unread()
        this.unread = data.unread || 0
      } catch (error) {
        this.unread = 0
      }
    },

    reset() {
      this.unread = 0
    }
  }
})
