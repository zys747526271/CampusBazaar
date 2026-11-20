<template>
  <div class="profile-page">
    <h1 class="page-title">个人中心</h1>
    <el-tabs v-model="activeTab">
      <!-- 基本信息 -->
      <el-tab-pane label="基本信息" name="basic">
        <el-card shadow="never">
          <div class="basic-layout">
            <div class="avatar-block">
              <el-avatar :size="90" :src="userStore.avatar">{{ userStore.displayName.charAt(0).toUpperCase() }}</el-avatar>
              <div class="roles">
                <el-tag v-if="userStore.isSeller" type="success" size="small">卖家</el-tag>
                <el-tag v-else size="small">买家</el-tag>
                <el-tag v-if="userStore.isAdmin" type="warning" size="small">管理员</el-tag>
              </div>
            </div>
            <el-form :model="form" :rules="rules" ref="formRef" label-width="90px" class="basic-form">
              <el-form-item label="昵称" prop="nickname">
                <el-input v-model="form.nickname" />
              </el-form-item>
              <el-form-item label="手机号" prop="phone">
                <el-input v-model="form.phone" disabled />
              </el-form-item>
              <el-form-item label="邮箱" prop="email">
                <el-input v-model="form.email" />
              </el-form-item>
              <el-form-item label="头像URL" prop="avatar_url">
                <el-input v-model="form.avatar_url" placeholder="https://..." />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="saving" @click="saveBasic">保存修改</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 修改密码 -->
      <el-tab-pane label="修改密码" name="password">
        <el-card shadow="never">
          <el-form :model="pwdForm" :rules="pwdRules" ref="pwdRef" label-width="90px" class="basic-form">
            <el-form-item label="原密码" prop="old_password">
              <el-input v-model="pwdForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="pwdForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="changePwd">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 收货地址 -->
      <el-tab-pane label="收货地址" name="address">
        <el-card shadow="never">
          <div class="address-head">
            <h3>我的收货地址</h3>
            <el-button type="primary" size="small" @click="openAddress()">添加地址</el-button>
          </div>
          <el-empty v-if="!addresses.length" description="暂无收货地址" />
          <div v-else class="address-grid">
            <el-card v-for="a in addresses" :key="a.id" shadow="hover" class="address-card">
              <div class="addr-line"><strong>{{ a.province }} {{ a.city }} {{ a.district }}</strong>
                <el-tag v-if="a.is_default" type="success" size="small">默认</el-tag>
              </div>
              <div class="addr-detail">{{ a.detail }}</div>
              <div class="addr-actions">
                <el-button v-if="!a.is_default" text size="small" @click="setDefault(a.id)">设为默认</el-button>
                <el-button text size="small" @click="openAddress(a)">编辑</el-button>
                <el-button text size="small" type="danger" @click="removeAddress(a.id)">删除</el-button>
              </div>
            </el-card>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="addrDialog" :title="editingAddr ? '编辑地址' : '添加地址'" width="500px">
      <el-form :model="addrForm" :rules="addrRules" ref="addrRef" label-width="90px">
        <el-form-item label="省份" prop="province"><el-input v-model="addrForm.province" /></el-form-item>
        <el-form-item label="城市" prop="city"><el-input v-model="addrForm.city" /></el-form-item>
        <el-form-item label="区/县" prop="district"><el-input v-model="addrForm.district" /></el-form-item>
        <el-form-item label="详细地址" prop="detail"><el-input v-model="addrForm.detail" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="默认"><el-switch v-model="addrForm.is_default" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addrDialog = false">取消</el-button>
        <el-button type="primary" @click="saveAddress">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import api from '@/utils/api'

const userStore = useUserStore()
const activeTab = ref('basic')
const saving = ref(false)
const formRef = ref(null)
const pwdRef = ref(null)
const addrRef = ref(null)

const form = reactive({ nickname: '', phone: '', email: '', avatar_url: '' })
const rules = {
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }]
}
const pwdForm = reactive({ old_password: '', new_password: '' })
const pwdRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, message: '至少6位', trigger: 'blur' }]
}

const addresses = ref([])
const addrDialog = ref(false)
const editingAddr = ref(false)
const addrForm = reactive({ id: null, province: '', city: '', district: '', detail: '', is_default: false })
const addrRules = {
  province: [{ required: true, message: '请输入省份', trigger: 'blur' }],
  city: [{ required: true, message: '请输入城市', trigger: 'blur' }],
  district: [{ required: true, message: '请输入区/县', trigger: 'blur' }],
  detail: [{ required: true, message: '请输入详细地址', trigger: 'blur' }]
}

const initForm = () => {
  const u = userStore.userInfo
  Object.assign(form, {
    nickname: u.nickname || '', phone: u.phone || '',
    email: u.email || '', avatar_url: u.avatar_url || ''
  })
}

const saveBasic = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async valid => {
    if (!valid) return
    saving.value = true
    try {
      const resp = await api.auth.updateProfile({ nickname: form.nickname, email: form.email, avatar_url: form.avatar_url })
      if (resp.success) {
        await userStore.fetchUserProfile()
        initForm()
        ElMessage.success('保存成功')
      } else {
        ElMessage.error(resp.message || '保存失败')
      }
    } catch (e) { ElMessage.error('保存失败') }
    finally { saving.value = false }
  })
}

const changePwd = async () => {
  if (!pwdRef.value) return
  await pwdRef.value.validate(async valid => {
    if (!valid) return
    try {
      const resp = await api.auth.changePassword(pwdForm)
      if (resp.success) {
        ElMessage.success('密码修改成功，请重新登录')
        userStore.logout()
        setTimeout(() => location.href = '/auth/login', 800)
      } else {
        ElMessage.error(resp.message || '修改失败')
      }
    } catch (e) { ElMessage.error('修改失败') }
  })
}

const loadAddresses = async () => {
  try {
    const resp = await api.addresses.getList()
    addresses.value = resp.data || []
  } catch (e) { addresses.value = [] }
}

const openAddress = (a = null) => {
  editingAddr.value = !!a
  Object.assign(addrForm, a
    ? { id: a.id, province: a.province, city: a.city, district: a.district, detail: a.detail, is_default: a.is_default }
    : { id: null, province: '', city: '', district: '', detail: '', is_default: false })
  addrDialog.value = true
}

const saveAddress = async () => {
  if (!addrRef.value) return
  await addrRef.value.validate(async valid => {
    if (!valid) return
    try {
      const payload = { ...addrForm }
      const resp = editingAddr.value ? await api.addresses.update(addrForm.id, payload) : await api.addresses.create(payload)
      if (resp.success) { ElMessage.success('已保存'); addrDialog.value = false; loadAddresses() }
      else ElMessage.error(resp.message || '保存失败')
    } catch (e) { ElMessage.error('保存失败') }
  })
}

const setDefault = async (id) => {
  try { await api.addresses.setDefault(id); ElMessage.success('已设为默认'); loadAddresses() }
  catch (e) { ElMessage.error('操作失败') }
}

const removeAddress = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除该地址吗？', '提示', { type: 'warning' })
    await api.addresses.remove(id); ElMessage.success('已删除'); loadAddresses()
  } catch (e) { /* ignore */ }
}

onMounted(() => { initForm(); loadAddresses() })
</script>

<style scoped>
.profile-page { min-height: 60vh; }
.page-title { font-size: 24px; color: #303133; margin-bottom: 20px; }
.basic-layout { display: flex; gap: 40px; flex-wrap: wrap; }
.avatar-block { text-align: center; }
.roles { margin-top: 12px; display: flex; gap: 6px; justify-content: center; }
.basic-form { flex: 1; min-width: 280px; max-width: 520px; }
.address-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.address-head h3 { font-size: 16px; }
.address-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.address-card .addr-line { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.address-card .addr-detail { color: #606266; font-size: 14px; margin-bottom: 12px; }
.address-card .addr-actions { display: flex; gap: 4px; }
</style>
