<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppIcon from '@/components/ui/AppIcon.vue'
import { pickFieldErrors } from '@/utils/format'

const router = useRouter()
const form = reactive({ username: '', name: '', password: '', confirm: '', invite_code: '' })
const errors = reactive({})
const loading = ref(false)

const submit = async () => {
  Object.keys(errors).forEach((key) => delete errors[key])
  if (form.username.trim().length < 3) errors.username = '账号至少 3 个字符'
  if (form.password.length < 8) errors.password = '密码至少 8 位'
  else if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) errors.password = '密码需包含字母和数字'
  if (form.password !== form.confirm) errors.confirm = '两次输入的密码不一致'
  if (Object.keys(errors).length) return

  loading.value = true
  try {
    await authApi.adminRegister({
      username: form.username.trim(),
      name: form.name.trim(),
      password: form.password,
      invite_code: form.invite_code.trim()
    })
    toastSuccess('管理员账号创建成功，请登录')
    router.replace('/admin/login')
  } catch (error) {
    Object.assign(errors, pickFieldErrors(error))
    toastError(error.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="admin-register">
    <div class="panel">
      <div class="brand">
        <span class="brand-mark"><AppIcon name="shield" :size="20" /></span>
        <div>
          <strong>管理员注册</strong>
          <small>需要平台开关开启，生产环境需邀请码</small>
        </div>
      </div>

      <form class="form" @submit.prevent="submit">
        <div class="grid-2">
          <div class="field">
            <label>管理员账号</label>
            <input v-model="form.username" class="input" :class="{ 'has-error': errors.username }" maxlength="40" placeholder="用于登录后台" />
            <span v-if="errors.username" class="field-error">{{ errors.username }}</span>
          </div>
          <div class="field">
            <label>姓名（选填）</label>
            <input v-model="form.name" class="input" maxlength="40" placeholder="真实姓名或昵称" />
          </div>
        </div>

        <div class="grid-2 mt-12">
          <div class="field">
            <label>密码</label>
            <input v-model="form.password" class="input" :class="{ 'has-error': errors.password }" type="password" maxlength="32" placeholder="至少 8 位，含字母与数字" />
            <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
          </div>
          <div class="field">
            <label>确认密码</label>
            <input v-model="form.confirm" class="input" :class="{ 'has-error': errors.confirm }" type="password" maxlength="32" />
            <span v-if="errors.confirm" class="field-error">{{ errors.confirm }}</span>
          </div>
        </div>

        <div class="field mt-12">
          <label>邀请码</label>
          <input v-model="form.invite_code" class="input" maxlength="64" placeholder="生产环境必填，本地环境可从 .env 查看" />
          <span class="field-hint">邀请码由平台负责人配置在 ADMIN_REGISTER_INVITE_CODE</span>
        </div>

        <button class="btn btn-primary btn-block mt-20" type="submit" :disabled="loading">
          {{ loading ? '提交中…' : '创建管理员账号' }}
        </button>
      </form>

      <div class="foot">
        <RouterLink to="/admin/login" class="text-xs">已有账号，去登录</RouterLink>
        <RouterLink to="/" class="text-xs">返回商城</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-register {
  min-height: 100vh; display: grid; place-items: center; padding: 24px;
  background: radial-gradient(circle at 80% 0%, #2a2118, #14171d 55%, #0e1116 100%);
}
.panel {
  width: min(520px, 100%);
  background: #fff; border-radius: 18px; padding: 32px 30px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, .35);
}
.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; }
.brand-mark {
  width: 42px; height: 42px; border-radius: 12px;
  background: linear-gradient(135deg, var(--brand-light), var(--brand));
  color: #fff; display: grid; place-items: center;
}
.brand strong { display: block; font-size: 16px; }
.brand small { color: var(--muted); font-size: 11.5px; }
.form { display: flex; flex-direction: column; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.mt-20 { margin-top: 20px; }
.foot { display: flex; justify-content: space-between; margin-top: 18px; }
.foot a { color: var(--muted); }
.foot a:hover { color: var(--brand); }
@media (max-width: 560px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
