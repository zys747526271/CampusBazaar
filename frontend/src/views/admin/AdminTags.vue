<script setup>
import { onMounted, reactive, ref } from 'vue'
import { adminApiClient } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppModal from '@/components/ui/AppModal.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'

const loading = ref(true)
const items = ref([])
const modalOpen = ref(false)
const editingId = ref(0)
const saving = ref(false)
const errors = reactive({})

const form = reactive({ name: '', icon: '', description: '', sort_order: 0, is_active: true })

const load = async () => {
  loading.value = true
  try {
    const data = await adminApiClient.tags()
    items.value = data.items || []
  } catch (error) {
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  editingId.value = 0
  Object.assign(form, { name: '', icon: '', description: '', sort_order: items.value.length + 1, is_active: true })
  Object.keys(errors).forEach((key) => delete errors[key])
  modalOpen.value = true
}

const openEdit = (tag) => {
  editingId.value = tag.id
  Object.assign(form, {
    name: tag.name,
    icon: tag.icon || '',
    description: tag.description || '',
    sort_order: tag.sort_order,
    is_active: tag.is_active
  })
  Object.keys(errors).forEach((key) => delete errors[key])
  modalOpen.value = true
}

const save = async () => {
  Object.keys(errors).forEach((key) => delete errors[key])
  if (!form.name.trim()) errors.name = '请填写分类名称'
  if (Object.keys(errors).length) return
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      icon: form.icon.trim(),
      description: form.description.trim(),
      sort_order: Number(form.sort_order) || 0,
      is_active: form.is_active
    }
    if (editingId.value) await adminApiClient.updateTag(editingId.value, payload)
    else await adminApiClient.createTag(payload)
    toastSuccess('分类已保存')
    modalOpen.value = false
    load()
  } catch (error) {
    Object.assign(errors, error.details || {})
    toastError(error.message)
  } finally {
    saving.value = false
  }
}

const toggleActive = async (tag) => {
  try {
    await adminApiClient.updateTag(tag.id, {
      name: tag.name,
      icon: tag.icon,
      description: tag.description,
      sort_order: tag.sort_order,
      is_active: !tag.is_active
    })
    tag.is_active = !tag.is_active
    toastSuccess(tag.is_active ? '分类已启用' : '分类已停用')
  } catch (error) {
    toastError(error.message)
  }
}

const remove = async (tag) => {
  const ok = await confirmAction({
    title: '删除分类',
    message: `分类「${tag.name}」下有 ${tag.product_count} 件商品。删除后商品仍可打开，但前台不再提供该分类入口。`,
    confirmText: '删除分类'
  })
  if (!ok) return
  try {
    const data = await adminApiClient.deleteTag(tag.id)
    toastSuccess(data.soft_deleted ? '分类已停用（仍有历史商品）' : '分类已删除')
    load()
  } catch (error) {
    toastError(error.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="admin-tags">
    <header class="head">
      <div>
        <h1>平台分类</h1>
        <p class="text-sm text-muted">全站导航与筛选的唯一来源，停用后买家侧不再展示</p>
      </div>
      <button class="btn btn-primary btn-sm" type="button" @click="openCreate">
        <AppIcon name="plus" :size="14" /> 新增分类
      </button>
    </header>

    <div class="panel">
      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 5" :key="i" :h="44" radius="8px" />
      </div>

      <AppEmpty v-else-if="!items.length" icon="tag" title="还没有平台分类" compact>
        <button class="btn btn-primary btn-sm" type="button" @click="openCreate">新增分类</button>
      </AppEmpty>

      <table v-else class="table">
        <thead>
          <tr><th>分类</th><th>描述</th><th>排序</th><th>商品数</th><th>状态</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="tag in items" :key="tag.id">
            <td><strong>{{ tag.name }}</strong></td>
            <td class="text-muted">{{ tag.description || '—' }}</td>
            <td>{{ tag.sort_order }}</td>
            <td>{{ tag.product_count }}</td>
            <td>
              <span class="tag" :class="tag.is_active ? 'tag-ok' : ''">{{ tag.is_active ? '启用' : '停用' }}</span>
            </td>
            <td>
              <div class="table-actions">
                <button class="btn btn-sm" type="button" @click="openEdit(tag)">编辑</button>
                <button class="btn btn-sm" type="button" @click="toggleActive(tag)">{{ tag.is_active ? '停用' : '启用' }}</button>
                <button class="btn btn-sm btn-danger" type="button" @click="remove(tag)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <AppModal v-model="modalOpen" :title="editingId ? '编辑分类' : '新增分类'" width="440px">
      <div class="field">
        <label>分类名称</label>
        <input v-model="form.name" class="input" :class="{ 'has-error': errors.name }" maxlength="20" placeholder="例如：教材书籍" />
        <span v-if="errors.name" class="field-error">{{ errors.name }}</span>
      </div>
      <div class="field mt-12">
        <label>图标标识（选填）</label>
        <input v-model="form.icon" class="input" maxlength="30" placeholder="例如：book / device" />
      </div>
      <div class="field mt-12">
        <label>描述（选填）</label>
        <input v-model="form.description" class="input" maxlength="120" placeholder="一句话说明这个分类" />
      </div>
      <div class="grid-2 mt-12">
        <div class="field">
          <label>排序</label>
          <input v-model="form.sort_order" class="input" inputmode="numeric" />
        </div>
        <label class="check"><input v-model="form.is_active" type="checkbox" /> 启用该分类</label>
      </div>
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
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.head h1 { font-size: 22px; }
.loading { display: flex; flex-direction: column; gap: 8px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: center; }
.check { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: var(--ink-2); margin-top: 18px; }
.check input { accent-color: var(--brand); }
</style>
