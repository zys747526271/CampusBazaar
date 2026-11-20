import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { setAuthFailureHandler } from './api'
import { useAuthStore } from './stores/auth'
import { toastWarn } from './composables/useToast'
import './styles/base.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// 401 统一出口：只清理对应身份的令牌并跳登录，403 仅由调用方提示（PRD 7.3）
setAuthFailureHandler((scope) => {
  const auth = useAuthStore(pinia)
  auth.onUnauthorized(scope)
  const current = router.currentRoute.value
  if (scope === 'admin') {
    if (current.path.startsWith('/admin') && current.path !== '/admin/login') {
      router.replace({ path: '/admin/login', query: { redirect: current.fullPath } })
    }
  } else if (current.meta.requiresAuth) {
    router.replace({ path: '/login', query: { redirect: current.fullPath } })
  }
  toastWarn('登录状态已失效，请重新登录')
})

router.isReady().then(() => {
  app.mount('#app')
  const boot = document.getElementById('boot')
  if (boot) boot.remove()
})
