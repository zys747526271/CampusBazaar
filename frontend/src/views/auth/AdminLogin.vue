<template>
  <div class="admin-auth-page">
    <div class="admin-auth-card">
      <div class="header">
        <div class="brand"><el-icon><Lock /></el-icon><span>校园集市 · 管理平台</span></div>
        <h2>管理员登录</h2>
        <p>仅限授权管理员访问</p>
      </div>
      <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" class="alert" />
      <el-form :model="form" :rules="rules" ref="formRef" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="管理员用户名" size="large" prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" class="submit" :loading="loading" @click="handleLogin">登录管理后台</el-button>
        </el-form-item>
      </el-form>
      <div class="footer">
        <p>测试环境可 <router-link to="/admin/register">注册管理员账号</router-link></p>
        <router-link to="/" class="back">← 返回前台</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async valid => {
    if (!valid) return
    loading.value = true
    errorMsg.value = ''
    const res = await userStore.adminLogin({ username: form.username, password: form.password })
    loading.value = false
    if (res.success) {
      ElMessage.success('管理员登录成功')
      router.push(route.query.redirect || '/admin')
    } else {
      errorMsg.value = res.message
    }
  })
}
</script>

<style scoped>
.admin-auth-page { min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #1f2d3d 0%, #304156 100%); padding: 20px; }
.admin-auth-card { width: 100%; max-width: 400px; background: #fff; border-radius: 12px; padding: 34px;
  box-shadow: 0 16px 50px rgba(0,0,0,.3); }
.header { text-align: center; margin-bottom: 24px; }
.header .brand { display: flex; align-items: center; justify-content: center; gap: 6px; color: #409eff;
  font-weight: 700; font-size: 17px; margin-bottom: 14px; }
.header h2 { font-size: 22px; color: #303133; margin-bottom: 6px; }
.header p { color: #909399; font-size: 13px; }
.submit { width: 100%; }
.alert { margin-bottom: 14px; }
.footer { text-align: center; color: #606266; font-size: 13px; margin-top: 10px; }
.footer a { color: #409eff; text-decoration: none; }
.footer .back { display: block; margin-top: 12px; color: #909399; }
</style>
