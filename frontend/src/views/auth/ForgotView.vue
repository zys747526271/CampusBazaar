<script setup>
import { onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api'
import { toastError, toastSuccess } from '@/composables/useToast'
import AuthShell from '@/components/layout/AuthShell.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { pickFieldErrors } from '@/utils/format'

const router = useRouter()
const form = reactive({ phone: '', code: '', new_password: '', confirm: '' })
const errors = reactive({})
const loading = ref(false)
const sending = ref(false)
const countdown = ref(0)
const devCode = ref('')
let timer = null

const startCountdown = () => {
  countdown.value = 60
  if (timer) window.clearInterval(timer)
  timer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      window.clearInterval(timer)
      timer = null
    }
  }, 1000)
}

const sendCode = async () => {
  if (!/^1[3-9]\d{9}$/.test(form.phone)) {
    errors.phone = '请先填写 11 位手机号'
    return
  }
  sending.value = true
  try {
    const data = await authApi.captcha({ phone: form.phone, scene: 'reset' })
    startCountdown()
    if (data.dev_code) {
      devCode.value = data.dev_code
      form.code = data.dev_code
      toastSuccess('验证码已生成（本地模式已自动填入）')
    } else {
      toastSuccess('验证码已发送')
    }
  } catch (error) {
    toastError(error.message)
  } finally {
    sending.value = false
  }
}

const submit = async () => {
  Object.keys(errors).forEach((key) => delete errors[key])
  if (!/^1[3-9]\d{9}$/.test(form.phone)) errors.phone = '请输入 11 位手机号'
  if (!/^\d{6}$/.test(form.code)) errors.code = '请输入 6 位验证码'
  if (form.new_password.length < 8) errors.new_password = '密码至少 8 位'
  else if (!/[A-Za-z]/.test(form.new_password) || !/\d/.test(form.new_password)) {
    errors.new_password = '密码需同时包含字母和数字'
  }
  if (form.new_password !== form.confirm) errors.confirm = '两次输入的密码不一致'
  if (Object.keys(errors).length) return

  loading.value = true
  try {
    await authApi.resetPassword({ phone: form.phone, code: form.code, new_password: form.new_password })
    toastSuccess('密码已重置，请使用新密码登录')
    router.replace({ path: '/login', query: { phone: form.phone } })
  } catch (error) {
    Object.assign(errors, pickFieldErrors(error))
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <AuthShell title="找回密码" subtitle="通过手机号验证身份，重设登录密码">
    <form class="form" @submit.prevent="submit">
      <div class="field">
        <label>注册手机号</label>
        <div class="input-wrap">
          <AppIcon name="user" :size="16" class="prefix" />
          <input
            v-model="form.phone"
            class="input with-icon"
            :class="{ 'has-error': errors.phone }"
            maxlength="11"
            inputmode="numeric"
            placeholder="请输入注册手机号"
          />
        </div>
        <span v-if="errors.phone" class="field-error">{{ errors.phone }}</span>
      </div>

      <div class="field mt-12">
        <label>验证码</label>
        <div class="code-row">
          <input v-model="form.code" class="input" :class="{ 'has-error': errors.code }" maxlength="6" inputmode="numeric" placeholder="6 位验证码" />
          <button class="btn code-btn" type="button" :disabled="sending || countdown > 0" @click="sendCode">
            {{ countdown > 0 ? `${countdown}s 后重发` : sending ? '发送中…' : '获取验证码' }}
          </button>
        </div>
        <span v-if="errors.code" class="field-error">{{ errors.code }}</span>
        <span v-if="devCode" class="field-hint text-brand">本地模式验证码：{{ devCode }}</span>
      </div>

      <div class="field mt-12">
        <label>新密码</label>
        <input
          v-model="form.new_password"
          class="input"
          :class="{ 'has-error': errors.new_password }"
          type="password"
          maxlength="32"
          placeholder="至少 8 位，含字母与数字"
        />
        <span v-if="errors.new_password" class="field-error">{{ errors.new_password }}</span>
      </div>

      <div class="field mt-12">
        <label>确认新密码</label>
        <input
          v-model="form.confirm"
          class="input"
          :class="{ 'has-error': errors.confirm }"
          type="password"
          maxlength="32"
          placeholder="再输入一次"
        />
        <span v-if="errors.confirm" class="field-error">{{ errors.confirm }}</span>
      </div>

      <button class="btn btn-primary btn-lg btn-block mt-24" type="submit" :disabled="loading">
        {{ loading ? '提交中…' : '重置密码' }}
      </button>

      <p class="switch mt-12">
        想起密码了？
        <RouterLink to="/login" class="link">返回登录</RouterLink>
      </p>
    </form>
  </AuthShell>
</template>

<style scoped>
.form { display: flex; flex-direction: column; }
.input-wrap { position: relative; display: flex; align-items: center; }
.prefix { position: absolute; left: 12px; color: var(--muted-2); pointer-events: none; }
.with-icon { padding-left: 38px; }
.code-row { display: grid; grid-template-columns: 1fr 132px; gap: 10px; }
.code-btn { height: 42px; white-space: nowrap; }
.link { color: var(--brand); }
.switch { text-align: center; font-size: 13px; color: var(--muted); }
@media (max-width: 560px) { .code-row { grid-template-columns: 1fr 116px; } }
</style>
