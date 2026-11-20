<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <div class="brand"><el-icon><Shop /></el-icon><span>校园集市</span></div>
        <h2>欢迎回来</h2>
        <p>登录后即可收藏、购买和管理订单</p>
      </div>

      <el-form :model="form" :rules="rules" ref="formRef" class="auth-form" @keyup.enter="handleLogin">
        <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" class="alert" />
        <el-form-item prop="phone">
          <el-input v-model="form.phone" placeholder="手机号" size="large" prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" prefix-icon="Lock" show-password />
        </el-form-item>
        <div class="options">
          <el-checkbox v-model="remember">记住我</el-checkbox>
          <span class="tip">忘记密码请联系管理员</span>
        </div>
        <el-form-item>
          <el-button type="primary" size="large" class="submit" :loading="loading" @click="handleLogin">登录</el-button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        <span>还没有账号？<router-link to="/auth/register">立即注册</router-link></span>
        <router-link to="/" class="back">← 返回首页浏览</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Shop } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const remember = ref(false)

const form = reactive({ phone: '', password: '' })
const rules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

onMounted(() => {
  const remembered = localStorage.getItem('rememberedPhone')
  if (remembered) { form.phone = remembered; remember.value = true }
})

const handleLogin = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async valid => {
    if (!valid) return
    loading.value = true
    errorMsg.value = ''
    // 统一走 store，确保顶部导航立即读到登录态
    const res = await userStore.login({ phone: form.phone, password: form.password })
    loading.value = false
    if (res.success) {
      if (remember.value) localStorage.setItem('rememberedPhone', form.phone)
      else localStorage.removeItem('rememberedPhone')
      ElMessage.success('登录成功')
      router.push(route.query.redirect || '/')
    } else {
      errorMsg.value = res.message
    }
  })
}
</script>

<style scoped>
.auth-page { min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #e0f0ff 0%, #f5f7fa 100%); padding: 20px; }
.auth-card { width: 100%; max-width: 420px; background: #fff; border-radius: 14px; padding: 36px;
  box-shadow: 0 12px 40px rgba(0,0,0,.1); }
.auth-header { text-align: center; margin-bottom: 26px; }
.auth-header .brand { display: flex; align-items: center; justify-content: center; gap: 6px;
  color: #409eff; font-weight: 700; font-size: 18px; margin-bottom: 16px; }
.auth-header h2 { font-size: 24px; color: #303133; margin-bottom: 8px; }
.auth-header p { color: #909399; font-size: 13px; }
.options { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.options .tip { color: #909399; font-size: 12px; }
.submit { width: 100%; }
.alert { margin-bottom: 16px; }
.auth-footer { text-align: center; color: #606266; font-size: 14px; margin-top: 10px; }
.auth-footer a { color: #409eff; text-decoration: none; }
.auth-footer .back { display: block; margin-top: 14px; color: #909399; font-size: 13px; }
</style>
