<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { useAppStore } from '@/stores/app'
import { toastError, toastSuccess } from '@/composables/useToast'
import AuthShell from '@/components/layout/AuthShell.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { pickFieldErrors } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const cart = useCartStore()
const app = useAppStore()

const form = reactive({ phone: '', password: '' })
const errors = reactive({})
const loading = ref(false)
const showPassword = ref(false)

const isDev = import.meta.env.DEV
const redirect = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : '/'))

const submit = async () => {
  Object.keys(errors).forEach((key) => delete errors[key])
  if (!/^1[3-9]\d{9}$/.test(form.phone)) errors.phone = '请输入 11 位手机号'
  if (!form.password) errors.password = '请输入密码'
  if (Object.keys(errors).length) return

  loading.value = true
  try {
    await auth.login({ phone: form.phone, password: form.password })
    await Promise.all([cart.refresh(), app.loadUnread()])
    toastSuccess(`欢迎回来，${auth.displayName}`)
    router.replace(redirect.value)
  } catch (error) {
    Object.assign(errors, pickFieldErrors(error))
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

const useDemo = (phone) => {
  form.phone = phone
  form.password = ''
}
</script>

<template>
  <AuthShell title="登录校园集市" subtitle="登录后即可收藏、加购、下单与评价">
    <form class="form" @submit.prevent="submit">
      <div class="field">
        <label>手机号</label>
        <div class="input-wrap">
          <AppIcon name="user" :size="16" class="prefix" />
          <input
            v-model="form.phone"
            class="input with-icon"
            :class="{ 'has-error': errors.phone }"
            maxlength="11"
            inputmode="numeric"
            placeholder="请输入注册手机号"
            autocomplete="username"
          />
        </div>
        <span v-if="errors.phone" class="field-error">{{ errors.phone }}</span>
      </div>

      <div class="field mt-16">
        <label>密码</label>
        <div class="input-wrap">
          <AppIcon name="shield" :size="16" class="prefix" />
          <input
            v-model="form.password"
            class="input with-icon with-suffix"
            :class="{ 'has-error': errors.password }"
            :type="showPassword ? 'text' : 'password'"
            maxlength="32"
            placeholder="请输入密码"
            autocomplete="current-password"
          />
          <button class="suffix" type="button" :aria-label="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword">
            <AppIcon name="eye" :size="16" />
          </button>
        </div>
        <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
      </div>

      <div class="row-between mt-12">
        <span class="text-xs text-muted">登录即表示同意《用户协议》与《隐私政策》</span>
        <RouterLink to="/forgot" class="text-xs link">忘记密码？</RouterLink>
      </div>

      <button class="btn btn-primary btn-lg btn-block mt-24" type="submit" :disabled="loading">
        {{ loading ? '登录中…' : '登录' }}
      </button>

      <p class="switch mt-16">
        还没有账号？
        <RouterLink :to="{ path: '/register', query: route.query }" class="link">立即注册</RouterLink>
      </p>

      <div v-if="isDev" class="demo">
        <p class="demo-title"><AppIcon name="info" :size="13" /> 本地演示账号（密码见 instance/demo-accounts.txt）</p>
        <div class="demo-btns">
          <button type="button" @click="useDemo('13800000004')">买家 13800000004</button>
          <button type="button" @click="useDemo('13800000001')">卖家 13800000001</button>
        </div>
        <p class="demo-admin">管理员请访问 <RouterLink to="/admin/login" class="link">/admin/login</RouterLink></p>
      </div>
    </form>
  </AuthShell>
</template>

<style scoped>
.form { display: flex; flex-direction: column; }
.input-wrap { position: relative; display: flex; align-items: center; }
.prefix { position: absolute; left: 12px; color: var(--muted-2); pointer-events: none; }
.with-icon { padding-left: 38px; }
.with-suffix { padding-right: 40px; }
.suffix {
  position: absolute; right: 8px; border: none; background: none;
  color: var(--muted); padding: 4px; line-height: 0; border-radius: 6px;
}
.suffix:hover { color: var(--ink-2); }

.link { color: var(--brand); }
.link:hover { text-decoration: underline; }
.switch { text-align: center; font-size: 13px; color: var(--muted); }

.demo { margin-top: 22px; border-top: 1px dashed var(--line); padding-top: 14px; }
.demo-title { display: flex; align-items: center; gap: 5px; font-size: 11.5px; color: var(--muted); }
.demo-btns { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
.demo-btns button {
  border: 1px solid var(--line-strong); background: #fafbfc;
  border-radius: 8px; padding: 6px 10px; font-size: 12px; color: var(--ink-2);
}
.demo-btns button:hover { border-color: var(--brand); color: var(--brand); }
.demo-admin { margin-top: 8px; font-size: 11.5px; color: var(--muted); }
</style>
