<script setup>
import { onMounted } from 'vue'
import ToastHost from '@/components/ui/ToastHost.vue'
import ConfirmHost from '@/components/ui/ConfirmHost.vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { useCartStore } from '@/stores/cart'

const auth = useAuthStore()
const app = useAppStore()
const cart = useCartStore()

onMounted(async () => {
  app.loadOptions()
  if (!auth.isLoggedIn) return
  try {
    await auth.fetchProfile()
    await Promise.all([cart.refresh(), app.loadUnread()])
  } catch (error) {
    /* 拦截器已处理 401 */
  }
})
</script>

<template>
  <RouterView />
  <ToastHost />
  <ConfirmHost />
</template>
