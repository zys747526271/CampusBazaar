<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { authApi, uploadApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppIcon from '@/components/ui/AppIcon.vue'
import { pickFieldErrors } from '@/utils/format'

const auth = useAuthStore()

const form = reactive({ nickname: '', email: '', campus: '', avatar_url: '' })
const errors = reactive({})
const saving = ref(false)
const uploading = ref(false)

const passwordForm = reactive({ old_password: '', new_password: '', confirm: '' })
const passwordErrors = reactive({})
const changing = ref(false)

const initial = computed(() => (auth.user?.nickname || '同').slice(0, 1))

const syncForm = () => {
  form.nickname = auth.user?.nickname || ''
  form.email = auth.user?.email || ''
  form.campus = auth.user?.campus || ''
  form.avatar_url = auth.user?.avatar_url || ''
}

const pickAvatar = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const data = await uploadApi.image(file)
    form.avatar_url = data.url
    toastSuccess('头像已上传，记得保存')
  } catch (error) {
    toastError(error.message)
  } finally {
    uploading.value = false
    event.target.value = ''
  }
}

const save = async () => {
  Object.keys(errors).forEach((key) => delete errors[key])
  if (!form.nickname.trim()) errors.nickname = '请填写昵称'
  if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) errors.email = '邮箱格式不正确'
  if (Object.keys(errors).length) return

  saving.value = true
  try {
    await auth.updateProfile({ ...form })
    toastSuccess('资料已保存')
  } catch (error) {
    Object.assign(errors, pickFieldErrors(error))
    toastError(error.message)
  } finally {
    saving.value = false
  }
}

const changePassword = async () => {
  Object.keys(passwordErrors).forEach((key) => delete passwordErrors[key])
  if (!passwordForm.old_password) passwordErrors.old_password = '请填写原密码'
  if (passwordForm.new_password.length < 8) passwordErrors.new_password = '新密码至少 8 位'
  else if (!/[A-Za-z]/.test(passwordForm.new_password) || !/\d/.test(passwordForm.new_password)) {
    passwordErrors.new_password = '新密码需同时包含字母和数字'
  }
  if (passwordForm.new_password !== passwordForm.confirm) passwordErrors.confirm = '两次输入的密码不一致'
  if (Object.keys(passwordErrors).length) return

  changing.value = true
  try {
    await authApi.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    toastSuccess('密码已修改')
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm = ''
  } catch (error) {
    Object.assign(passwordErrors, pickFieldErrors(error))
    toastError(error.message)
  } finally {
    changing.value = false
  }
}

onMounted(async () => {
  try {
    await auth.fetchProfile(true)
  } catch (error) {
    /* 忽略，仍展示已有信息 */
  }
  syncForm()
})
</script>

<template>
  <div class="profile">
    <section class="panel">
      <div class="head">
        <h1>个人中心</h1>
        <p class="text-sm text-muted">完善资料有助于卖家更快认出你</p>
      </div>

      <div class="avatar-row">
        <span class="avatar">
          <img v-if="form.avatar_url" :src="form.avatar_url" alt="" />
          <template v-else>{{ initial }}</template>
        </span>
        <div class="avatar-actions">
          <label class="btn btn-sm upload-btn">
            <AppIcon name="camera" :size="15" />
            {{ uploading ? '上传中…' : '更换头像' }}
            <input type="file" accept="image/jpeg,image/png,image/webp" hidden :disabled="uploading" @change="pickAvatar" />
          </label>
          <span class="text-xs text-muted">支持 JPG / PNG / WebP，单张不超过 5MB</span>
        </div>
        <div class="identity">
          <span class="tag" :class="auth.isSeller ? 'tag-brand' : 'tag-line'">
            {{ auth.isSeller ? '卖家 · 买家' : '买家' }}
          </span>
          <span class="text-xs text-muted">{{ auth.user?.phone }}</span>
        </div>
      </div>

      <div class="form-grid">
        <div class="field">
          <label>昵称</label>
          <input v-model="form.nickname" class="input" :class="{ 'has-error': errors.nickname }" maxlength="20" />
          <span v-if="errors.nickname" class="field-error">{{ errors.nickname }}</span>
        </div>
        <div class="field">
          <label>校区</label>
          <input v-model="form.campus" class="input" maxlength="30" placeholder="例如：东校区" />
        </div>
        <div class="field field-wide">
          <label>邮箱（选填）</label>
          <input v-model="form.email" class="input" :class="{ 'has-error': errors.email }" maxlength="120" placeholder="用于接收重要通知" />
          <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
        </div>
      </div>

      <div class="actions">
        <button class="btn btn-primary" type="button" :disabled="saving" @click="save">
          {{ saving ? '保存中…' : '保存资料' }}
        </button>
        <button class="btn" type="button" @click="syncForm">重置</button>
      </div>
    </section>

    <section class="panel">
      <div class="head">
        <h2>修改密码</h2>
        <p class="text-sm text-muted">修改后请使用新密码重新登录其他设备</p>
      </div>
      <div class="form-grid">
        <div class="field">
          <label>原密码</label>
          <input v-model="passwordForm.old_password" class="input" type="password" :class="{ 'has-error': passwordErrors.old_password }" maxlength="32" />
          <span v-if="passwordErrors.old_password" class="field-error">{{ passwordErrors.old_password }}</span>
        </div>
        <div class="field">
          <label>新密码</label>
          <input v-model="passwordForm.new_password" class="input" type="password" :class="{ 'has-error': passwordErrors.new_password }" maxlength="32" placeholder="至少 8 位，含字母与数字" />
          <span v-if="passwordErrors.new_password" class="field-error">{{ passwordErrors.new_password }}</span>
        </div>
        <div class="field">
          <label>确认新密码</label>
          <input v-model="passwordForm.confirm" class="input" type="password" :class="{ 'has-error': passwordErrors.confirm }" maxlength="32" />
          <span v-if="passwordErrors.confirm" class="field-error">{{ passwordErrors.confirm }}</span>
        </div>
      </div>
      <div class="actions">
        <button class="btn btn-dark" type="button" :disabled="changing" @click="changePassword">
          {{ changing ? '提交中…' : '修改密码' }}
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.profile { display: flex; flex-direction: column; gap: 14px; }
.head { margin-bottom: 18px; }
.head h1 { font-size: 21px; letter-spacing: -.3px; }
.head h2 { font-size: 17px; }

.avatar-row { display: flex; align-items: center; gap: 16px; padding-bottom: 18px; border-bottom: 1px dashed var(--line); }
.avatar {
  width: 68px; height: 68px; border-radius: 50%; flex: none;
  display: grid; place-items: center; font-size: 24px; font-weight: 700; color: #a03c0d;
  background: linear-gradient(135deg, #ffe2d3, #ffc3a6); overflow: hidden;
}
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.avatar-actions { display: flex; flex-direction: column; gap: 6px; }
.upload-btn { cursor: pointer; }
.identity { margin-left: auto; display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }

.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 18px; }
.field-wide { grid-column: 1 / -1; }
.actions { display: flex; gap: 10px; margin-top: 18px; }

@media (max-width: 640px) {
  .form-grid { grid-template-columns: 1fr; }
  .identity { display: none; }
}
</style>
