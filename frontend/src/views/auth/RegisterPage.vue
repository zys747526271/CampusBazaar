<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <div class="brand"><el-icon><Shop /></el-icon><span>校园集市</span></div>
        <h2>创建账号</h2>
        <p>加入校园集市，让闲置流转起来</p>
      </div>

      <el-form :model="form" :rules="rules" ref="formRef" class="auth-form" @keyup.enter="handleRegister">
        <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" class="alert" />
        <el-alert v-if="devCode" :title="`测试验证码：${devCode}（已同时显示在后端控制台，有效期5分钟）`"
          type="warning" show-icon :closable="false" class="alert" />

        <el-form-item prop="nickname">
          <el-input v-model="form.nickname" placeholder="昵称" size="large" prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="phone">
          <el-input v-model="form.phone" placeholder="手机号" size="large" prefix-icon="Phone" />
        </el-form-item>
        <el-form-item prop="email">
          <el-input v-model="form.email" placeholder="邮箱（选填）" size="large" prefix-icon="Message" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码（至少6位）" size="large" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="确认密码" size="large" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item prop="captcha">
          <div class="captcha-row">
            <el-input v-model="form.captcha" placeholder="验证码" size="large" />
            <el-button size="large" :disabled="countdown > 0 || sending" @click="getCaptcha">
              {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" class="submit" :loading="loading" @click="handleRegister">注册</el-button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        <span>已有账号？<router-link to="/auth/login">立即登录</router-link></span>
        <router-link to="/" class="back">← 返回首页浏览</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Shop } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import api from '@/utils/api'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)
const sending = ref(false)
const countdown = ref(0)
const errorMsg = ref('')
const devCode = ref('')
let timer = null

const form = reactive({ nickname: '', phone: '', email: '', password: '', confirmPassword: '', captcha: '' })

const validateConfirm = (rule, value, callback) => {
  if (value !== form.password) callback(new Error('两次输入密码不一致'))
  else callback()
}

const rules = {
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }, { min: 2, max: 20, message: '昵称2-20字符', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }, { pattern: /^1[3-9]\d{9}$/, message: '请输入有效手机号', trigger: 'blur' }],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码至少6位', trigger: 'blur' }],
  confirmPassword: [{ required: true, message: '请确认密码', trigger: 'blur' }, { validator: validateConfirm, trigger: 'blur' }],
  captcha: [{ required: true, message: '请输入验证码', trigger: 'blur' }]
}

const getCaptcha = async () => {
  if (!/^1[3-9]\d{9}$/.test(form.phone)) {
    ElMessage.warning('请先填写正确的手机号')
    return
  }
  sending.value = true
  try {
    const resp = await api.auth.captcha({ phone: form.phone })
    if (resp.success) {
      // 测试模式后端回显 dev_code；生产模式无此字段
      devCode.value = resp.data?.dev_code || ''
      ElMessage.success(devCode.value ? '验证码已生成（测试模式）' : '验证码已发送，请注意查收')
      countdown.value = 60
      timer = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) clearInterval(timer)
      }, 1000)
    } else {
      ElMessage.error(resp.message || '验证码发送失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '验证码发送失败')
  } finally {
    sending.value = false
  }
}

const handleRegister = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async valid => {
    if (!valid) return
    loading.value = true
    errorMsg.value = ''
    const res = await userStore.register({
      nickname: form.nickname, phone: form.phone,
      email: form.email || undefined, password: form.password, captcha: form.captcha
    })
    loading.value = false
    if (res.success) {
      ElMessage.success('注册成功，请登录')
      router.push('/auth/login')
    } else {
      errorMsg.value = res.message
    }
  })
}

onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.auth-page { min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #e0f0ff 0%, #f5f7fa 100%); padding: 20px; }
.auth-card { width: 100%; max-width: 440px; background: #fff; border-radius: 14px; padding: 32px 36px;
  box-shadow: 0 12px 40px rgba(0,0,0,.1); max-height: 95vh; overflow-y: auto; }
.auth-header { text-align: center; margin-bottom: 20px; }
.auth-header .brand { display: flex; align-items: center; justify-content: center; gap: 6px;
  color: #409eff; font-weight: 700; font-size: 18px; margin-bottom: 14px; }
.auth-header h2 { font-size: 23px; color: #303133; margin-bottom: 6px; }
.auth-header p { color: #909399; font-size: 13px; }
.captcha-row { display: flex; gap: 10px; width: 100%; }
.captcha-row .el-button { width: 120px; }
.submit { width: 100%; }
.alert { margin-bottom: 14px; }
.auth-footer { text-align: center; color: #606266; font-size: 14px; margin-top: 8px; }
.auth-footer a { color: #409eff; text-decoration: none; }
.auth-footer .back { display: block; margin-top: 12px; color: #909399; font-size: 13px; }
</style>
