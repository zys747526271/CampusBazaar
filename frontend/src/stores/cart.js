import { defineStore } from 'pinia'
import { cartApi } from '@/api'
import { useAuthStore } from './auth'

export const useCartStore = defineStore('cart', {
  state: () => ({
    count: 0,
    loading: false
  }),

  getters: {
    badge: (state) => (state.count > 99 ? '99+' : state.count)
  },

  actions: {
    async refresh() {
      const auth = useAuthStore()
      if (!auth.isLoggedIn) {
        this.count = 0
        return
      }
      try {
        const data = await cartApi.count()
        this.count = data.count || 0
      } catch (error) {
        this.count = 0
      }
    },

    async add(productId, quantity = 1) {
      const data = await cartApi.add({ product_id: productId, quantity })
      this.count = data.count || this.count + quantity
      return data
    },

    setCount(value) {
      this.count = Math.max(0, Number(value) || 0)
    },

    reset() {
      this.count = 0
    }
  }
})
