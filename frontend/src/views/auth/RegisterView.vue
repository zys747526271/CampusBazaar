<script setup>
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { toastError, toastSuccess } from '@/composables/useToast'
import AuthShell from '@/components/layout/AuthShell.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { pickFieldErrors } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const app = useAppStore()

const form = reactive({ phone: '', code: '', nickname: '', password: '', confirm: '', campus: '', agree_terms: false })
const errors = reactive({})
const loading = ref(false)
const sending = ref(false)
const countdown = ref(0)
const devCode = ref('')
let timer = null

const isDev = import.meta.env.DEV
const redirect = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : '/'))

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
    const data = await authApi.captcha({ phone: form.phone, scene: 'register' })
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
  if (!form.nickname.trim()) errors.nickname = '请填写昵称'
  if (form.password.length < 8) errors.password = '密码至少 8 位'
  else if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) errors.password = '密码需同时包含字母和数字'
  if (form.password !== form.confirm) errors.confirm = '两次输入的密码不一致'
  if (!form.agree_terms) errors.agree_terms = '请先同意用户协议与隐私政策'
  if (Object.keys(errors).length) return

  loading.value = true
  try {
    await auth.register({
      phone: form.phone,
      password: form.password,
      nickname: form.nickname.trim(),
      code: form.code,
      campus: form.campus.trim(),
      agree_terms: true
    })
    app.loadUnread()
    toastSuccess('注册成功，欢迎加入校园集市')
    router.replace(redirect.value)
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
  <AuthShell title="注册校园集市" subtitle="只需手机号，30 秒开启同校二手交易">
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
            placeholder="请输入手机号"
            autocomplete="tel"
          />
        </div>
        <span v-if="errors.phone" class="field-error">{{ errors.phone }}</span>
      </div>

      <div class="field mt-12">
        <label>短信验证码</label>
        <div class="code-row">
          <input
            v-model="form.code"
            class="input"
            :class="{ 'has-error': errors.code }"
            maxlength="6"
            inputmode="numeric"
            placeholder="6 位验证码"
          />
          <button class="btn code-btn" type="button" :disabled="sending || countdown > 0" @click="sendCode">
            {{ countdown > 0 ? `${countdown}s 后重发` : sending ? '发送中…' : '获取验证码' }}
          </button>
        </div>
        <span v-if="errors.code" class="field-error">{{ errors.code }}</span>
        <span v-if="devCode" class="field-hint text-brand">本地模式验证码：{{ devCode }}（也可在 /dev/captchas 查看）</span>
      </div>

      <div class="field mt-12">
        <label>昵称</label>
        <input
          v-model="form.nickname"
          class="input"
          :class="{ 'has-error': errors.nickname }"
          maxlength="20"
          placeholder="同学们怎么称呼你"
        />
        <span v-if="errors.nickname" class="field-error">{{ errors.nickname }}</span>
      </div>

      <div class="field mt-12">
        <label>校区（选填）</label>
        <input v-model="form.campus" class="input" maxlength="30" placeholder="例如：东校区" />
      </div>

      <div class="grid-2 mt-12">
        <div class="field">
          <label>设置密码</label>
          <input
            v-model="form.password"
            class="input"
            :class="{ 'has-error': errors.password }"
            type="password"
            maxlength="32"
            placeholder="至少 8 位，含字母与数字"
            autocomplete="new-password"
          />
          <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
        </div>
        <div class="field">
          <label>确认密码</label>
          <input
            v-model="form.confirm"
            class="input"
            :class="{ 'has-error': errors.confirm }"
            type="password"
            maxlength="32"
            placeholder="再输入一次"
            autocomplete="new-password"
          />
          <span v-if="errors.confirm" class="field-error">{{ errors.confirm }}</span>
        </div>
      </div>

      <label class="agree mt-16">
        <input v-model="form.agree_terms" type="checkbox" />
        <span>我已阅读并同意《用户协议》与《隐私政策》，承诺发布真实合法的商品信息</span>
      </label>
      <span v-if="errors.agree_terms" class="field-error">{{ errors.agree_terms }}</span>

      <button class="btn btn-primary btn-lg btn-block mt-16" type="submit" :disabled="loading">
        {{ loading ? '注册中…' : '注册并登录' }}
      </button>

      <p class="switch mt-12">
        已有账号？
        <RouterLink :to="{ path: '/login', query: route.query }" class="link">直接登录</RouterLink>
      </p>

      <p v-if="isDev" class="dev-hint">
        <AppIcon name="info" :size="13" /> 本地模式不会真的发短信，验证码会直接显示在页面上
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

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.agree { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; color: var(--muted); line-height: 1.6; }
.agree input { margin-top: 2px; accent-color: var(--brand); }
.link { color: var(--brand); }
.switch { text-align: center; font-size: 13px; color: var(--muted); }
.dev-hint {
  margin-top: 14px; display: flex; align-items: center; gap: 5px;
  font-size: 11.5px; color: var(--muted); justify-content: center;
}

@media (max-width: 560px) {
  .grid-2 { grid-template-columns: 1fr; }
  .code-row { grid-template-columns: 1fr 116px; }
}
</style>
