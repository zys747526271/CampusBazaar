<template>
  <div class="admin-auth-page">
    <div class="admin-auth-card">
      <div class="header">
        <div class="brand"><el-icon><Lock /></el-icon><span>校园集市 · 管理平台</span></div>
        <h2>管理员注册</h2>
        <p class="warning">此页面为独立管理入口，不面向普通用户</p>
      </div>
      <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" class="alert" />
      <el-form :model="form" :rules="rules" ref="formRef">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="管理员用户名" size="large" prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="email">
          <el-input v-model="form.email" placeholder="邮箱" size="large" prefix-icon="Message" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码（至少6位）" size="large" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="确认密码" size="large" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item prop="invite_code">
          <el-input v-model="form.invite_code" placeholder="邀请码（生产环境必填）" size="large" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" class="submit" :loading="loading" @click="handleRegister">注册管理员</el-button>
        </el-form-item>
      </el-form>
      <div class="footer">
        <p>已有账号？<router-link to="/admin/login">管理员登录</router-link></p>
        <router-link to="/" class="back">← 返回前台</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import api from '@/utils/api'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const form = reactive({ username: '', email: '', password: '', confirmPassword: '', invite_code: '' })

const validateConfirm = (rule, value, callback) => {
  if (value !== form.password) callback(new Error('两次输入密码不一致'))
  else callback()
}
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, message: '至少3字符', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码至少6位', trigger: 'blur' }],
  confirmPassword: [{ required: true, message: '请确认密码', trigger: 'blur' }, { validator: validateConfirm, trigger: 'blur' }]
}

const handleRegister = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async valid => {
    if (!valid) return
    loading.value = true
    errorMsg.value = ''
    try {
      const resp = await api.auth.adminRegister({
        username: form.username, email: form.email, password: form.password,
        invite_code: form.invite_code || undefined
      })
      if (resp.success) {
        ElMessage.success('管理员注册成功，请登录')
        router.push('/admin/login')
      } else {
        errorMsg.value = resp.message
      }
    } catch (e) {
      errorMsg.value = e.response?.data?.message || '注册失败'
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.admin-auth-page { min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #1f2d3d 0%, #304156 100%); padding: 20px; }
.admin-auth-card { width: 100%; max-width: 420px; background: #fff; border-radius: 12px; padding: 30px 34px;
  box-shadow: 0 16px 50px rgba(0,0,0,.3); }
.header { text-align: center; margin-bottom: 20px; }
.header .brand { display: flex; align-items: center; justify-content: center; gap: 6px; color: #409eff;
  font-weight: 700; font-size: 17px; margin-bottom: 12px; }
.header h2 { font-size: 22px; color: #303133; margin-bottom: 6px; }
.header .warning { color: #e6a23c; font-size: 12px; }
.submit { width: 100%; }
.alert { margin-bottom: 14px; }
.footer { text-align: center; color: #606266; font-size: 13px; margin-top: 10px; }
.footer a { color: #409eff; text-decoration: none; }
.footer .back { display: block; margin-top: 12px; color: #909399; }
</style>
