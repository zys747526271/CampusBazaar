<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppIcon from '@/components/ui/AppIcon.vue'
import { pickFieldErrors } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const form = reactive({ username: '', password: '' })
const errors = reactive({})
const loading = ref(false)

const submit = async () => {
  Object.keys(errors).forEach((key) => delete errors[key])
  if (form.username.trim().length < 3) errors.username = '请输入管理员账号'
  if (!form.password) errors.password = '请输入密码'
  if (Object.keys(errors).length) return

  loading.value = true
  try {
    const data = await auth.adminLogin({ username: form.username.trim(), password: form.password })
    toastSuccess(`欢迎，${data.admin?.name || data.admin?.username}`)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/admin'
    router.replace(redirect.startsWith('/admin') ? redirect : '/admin')
  } catch (error) {
    Object.assign(errors, pickFieldErrors(error))
    toastError(error.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="admin-login">
    <div class="panel">
      <div class="brand">
        <span class="brand-mark"><AppIcon name="shield" :size="20" /></span>
        <div>
          <strong>校园集市 · 管理后台</strong>
          <small>仅限运营与指导教师使用</small>
        </div>
      </div>

      <form class="form" @submit.prevent="submit">
        <div class="field">
          <label>管理员账号</label>
          <input
            v-model="form.username"
            class="input"
            :class="{ 'has-error': errors.username }"
            maxlength="40"
            placeholder="请输入账号"
            autocomplete="username"
          />
          <span v-if="errors.username" class="field-error">{{ errors.username }}</span>
        </div>
        <div class="field mt-12">
          <label>密码</label>
          <input
            v-model="form.password"
            class="input"
            :class="{ 'has-error': errors.password }"
            type="password"
            maxlength="64"
            placeholder="请输入密码"
            autocomplete="current-password"
          />
          <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
        </div>

        <button class="btn btn-primary btn-block mt-20" type="submit" :disabled="loading">
          {{ loading ? '登录中…' : '登录后台' }}
        </button>
      </form>

      <div class="foot">
        <RouterLink to="/" class="text-xs">返回商城前台</RouterLink>
        <RouterLink to="/admin/register" class="text-xs">管理员注册</RouterLink>
      </div>

      <p class="hint">
        <AppIcon name="info" :size="13" />
        连续 5 次密码错误将锁定 15 分钟；演示管理员账号见 instance/demo-accounts.txt
      </p>
    </div>
  </div>
</template>

<style scoped>
.admin-login {
  min-height: 100vh; display: grid; place-items: center; padding: 24px;
  background: radial-gradient(circle at 20% 10%, #2a2118, #14171d 55%, #0e1116 100%);
}
.panel {
  width: min(420px, 100%);
  background: #fff; border-radius: 18px; padding: 32px 30px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, .35);
}
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 26px; }
.brand-mark {
  width: 42px; height: 42px; border-radius: 12px;
  background: linear-gradient(135deg, var(--brand-light), var(--brand));
  color: #fff; display: grid; place-items: center;
}
.brand strong { display: block; font-size: 16px; }
.brand small { color: var(--muted); font-size: 11.5px; }

.form { display: flex; flex-direction: column; }
.mt-20 { margin-top: 20px; }
.foot { display: flex; justify-content: space-between; margin-top: 18px; }
.foot a { color: var(--muted); }
.foot a:hover { color: var(--brand); }
.hint {
  margin-top: 18px; padding-top: 14px; border-top: 1px dashed var(--line);
  display: flex; align-items: flex-start; gap: 5px;
  color: var(--muted); font-size: 11.5px; line-height: 1.6;
}
</style>
