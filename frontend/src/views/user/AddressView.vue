<script setup>
import { onMounted, reactive, ref } from 'vue'
import { addressApi } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppModal from '@/components/ui/AppModal.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { pickFieldErrors } from '@/utils/format'

const loading = ref(true)
const items = ref([])
const modalOpen = ref(false)
const editingId = ref(0)
const saving = ref(false)
const errors = reactive({})
const form = reactive({ name: '', phone: '', campus_area: '', detail: '', is_default: false })

const load = async () => {
  loading.value = true
  try {
    const data = await addressApi.list()
    items.value = data.items || []
  } catch (error) {
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  editingId.value = 0
  Object.assign(form, { name: '', phone: '', campus_area: '', detail: '', is_default: items.value.length === 0 })
  Object.keys(errors).forEach((key) => delete errors[key])
  modalOpen.value = true
}

const openEdit = (address) => {
  editingId.value = address.id
  Object.assign(form, {
    name: address.name,
    phone: address.phone,
    campus_area: address.campus_area,
    detail: address.detail,
    is_default: address.is_default
  })
  Object.keys(errors).forEach((key) => delete errors[key])
  modalOpen.value = true
}

const save = async () => {
  Object.keys(errors).forEach((key) => delete errors[key])
  if (!form.name.trim()) errors.name = '请填写联系人'
  if (!/^1[3-9]\d{9}$/.test(form.phone)) errors.phone = '请填写 11 位手机号'
  if (form.detail.trim().length < 2) errors.detail = '请填写详细地址'
  if (Object.keys(errors).length) return

  saving.value = true
  try {
    if (editingId.value) await addressApi.update(editingId.value, { ...form })
    else await addressApi.create({ ...form })
    toastSuccess('地址已保存')
    modalOpen.value = false
    load()
  } catch (error) {
    Object.assign(errors, pickFieldErrors(error))
    toastError(error.message)
  } finally {
    saving.value = false
  }
}

const setDefault = async (address) => {
  try {
    await addressApi.setDefault(address.id)
    toastSuccess('已设为默认地址')
    load()
  } catch (error) {
    toastError(error.message)
  }
}

const remove = async (address) => {
  const ok = await confirmAction({
    title: '删除地址',
    message: `确定删除「${address.campus_area} ${address.detail}」吗？`,
    confirmText: '删除'
  })
  if (!ok) return
  try {
    await addressApi.remove(address.id)
    toastSuccess('地址已删除')
    load()
  } catch (error) {
    toastError(error.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="addresses">
    <div class="panel">
      <header class="head">
        <div>
          <h1>收货地址</h1>
          <p class="text-sm text-muted">用于结算时快速选择交易地点</p>
        </div>
        <button class="btn btn-primary btn-sm" type="button" @click="openCreate">
          <AppIcon name="plus" :size="14" /> 新增地址
        </button>
      </header>

      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 3" :key="i" :h="72" radius="10px" />
      </div>

      <AppEmpty
        v-else-if="!items.length"
        icon="map-pin"
        title="还没有收货地址"
        description="添加常用交易地点，下单时不用重复填写"
      >
        <button class="btn btn-primary btn-sm" type="button" @click="openCreate">新增地址</button>
      </AppEmpty>

      <ul v-else class="list">
        <li v-for="address in items" :key="address.id" class="item">
          <div class="item-main">
            <div class="item-top">
              <strong>{{ address.name }}</strong>
              <span>{{ address.phone }}</span>
              <span v-if="address.is_default" class="tag tag-brand">默认</span>
            </div>
            <p class="text-sm text-muted">{{ address.campus_area }} {{ address.detail }}</p>
          </div>
          <div class="item-ops">
            <button v-if="!address.is_default" class="btn btn-sm" type="button" @click="setDefault(address)">设为默认</button>
            <button class="btn btn-sm" type="button" @click="openEdit(address)">编辑</button>
            <button class="btn btn-sm btn-danger" type="button" @click="remove(address)">删除</button>
          </div>
        </li>
      </ul>
    </div>

    <AppModal v-model="modalOpen" :title="editingId ? '编辑地址' : '新增地址'" width="460px">
      <div class="form-grid">
        <div class="field">
          <label>联系人</label>
          <input v-model="form.name" class="input" :class="{ 'has-error': errors.name }" maxlength="30" />
          <span v-if="errors.name" class="field-error">{{ errors.name }}</span>
        </div>
        <div class="field">
          <label>手机号</label>
          <input v-model="form.phone" class="input" :class="{ 'has-error': errors.phone }" maxlength="11" inputmode="numeric" />
          <span v-if="errors.phone" class="field-error">{{ errors.phone }}</span>
        </div>
        <div class="field field-wide">
          <label>校区 / 区域</label>
          <input v-model="form.campus_area" class="input" maxlength="60" placeholder="例如：东校区 3 号楼" />
        </div>
        <div class="field field-wide">
          <label>详细地址</label>
          <input v-model="form.detail" class="input" :class="{ 'has-error': errors.detail }" maxlength="200" placeholder="楼栋 / 门牌 / 自提点" />
          <span v-if="errors.detail" class="field-error">{{ errors.detail }}</span>
        </div>
      </div>
      <label class="check mt-12"><input v-model="form.is_default" type="checkbox" /> 设为默认地址</label>
      <template #footer>
        <button class="btn" type="button" @click="modalOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="saving" @click="save">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.head h1 { font-size: 21px; letter-spacing: -.3px; }
.loading { display: flex; flex-direction: column; gap: 10px; }

.list { display: flex; flex-direction: column; gap: 10px; }
.item {
  display: flex; align-items: center; gap: 16px;
  border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px;
}
.item:hover { border-color: var(--line-strong); background: #fcfdfe; }
.item-main { flex: 1; min-width: 0; }
.item-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.item-top span { color: var(--muted); font-size: 12.5px; }
.item-main p { margin-top: 4px; }
.item-ops { display: flex; gap: 8px; flex-wrap: wrap; }

.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.field-wide { grid-column: 1 / -1; }
.check { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: var(--ink-2); }
.check input { accent-color: var(--brand); }

@media (max-width: 640px) {
  .item { flex-direction: column; align-items: flex-start; }
  .form-grid { grid-template-columns: 1fr; }
}
</style>
