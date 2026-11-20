<script setup>
import { onMounted, reactive, ref } from 'vue'
import { sellerApi } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import PageHeader from '@/components/ui/PageHeader.vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'

const loading = ref(true)
const items = ref([])
const modalOpen = ref(false)
const editingId = ref(0)
const saving = ref(false)
const form = reactive({ name: '', sort_order: 0 })

const load = async () => {
  loading.value = true
  try {
    const data = await sellerApi.categories()
    items.value = data.items || []
  } catch (error) {
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  editingId.value = 0
  form.name = ''
  form.sort_order = items.value.length
  modalOpen.value = true
}

const openEdit = (category) => {
  editingId.value = category.id
  form.name = category.name
  form.sort_order = category.sort_order
  modalOpen.value = true
}

const save = async () => {
  if (!form.name.trim()) {
    toastError('请填写分类名称')
    return
  }
  saving.value = true
  try {
    const payload = { name: form.name.trim(), sort_order: Number(form.sort_order) || 0 }
    if (editingId.value) await sellerApi.updateCategory(editingId.value, payload)
    else await sellerApi.createCategory(payload)
    toastSuccess('分类已保存')
    modalOpen.value = false
    load()
  } catch (error) {
    toastError(error.message)
  } finally {
    saving.value = false
  }
}

const remove = async (category) => {
  const ok = await confirmAction({
    title: '删除分类',
    message: `确定删除分类「${category.name}」吗？分类下有商品时无法删除。`,
    confirmText: '删除'
  })
  if (!ok) return
  try {
    await sellerApi.deleteCategory(category.id)
    toastSuccess('分类已删除')
    load()
  } catch (error) {
    toastError(error.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="seller-categories">
    <PageHeader title="自定义分类" subtitle="只用于整理你自己的商品，不会影响全站分类">
      <template #actions>
        <button class="btn btn-primary btn-sm" type="button" @click="openCreate">
          <AppIcon name="plus" :size="14" /> 新建分类
        </button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="alert">
        <AppIcon name="info" :size="15" />
        平台分类决定买家怎么找到你，自定义分类只用于你自己管理。发布商品时两者可同时选择。
      </div>

      <div v-if="loading" class="loading mt-16">
        <SkeletonBlock v-for="i in 4" :key="i" :h="52" radius="8px" />
      </div>

      <AppEmpty
        v-else-if="!items.length"
        icon="layers"
        title="还没有自定义分类"
        description="按「考研资料」「宿舍小家电」等维度整理商品，管理更清晰"
        compact
      >
        <button class="btn btn-primary btn-sm" type="button" @click="openCreate">新建分类</button>
      </AppEmpty>

      <ul v-else class="list mt-12">
        <li v-for="category in items" :key="category.id" class="item">
          <span class="order">{{ category.sort_order }}</span>
          <div class="info">
            <strong>{{ category.name }}</strong>
            <span class="text-xs text-muted">{{ category.product_count }} 件商品</span>
          </div>
          <div class="ops">
            <button class="btn btn-sm" type="button" @click="openEdit(category)">重命名</button>
            <button class="btn btn-sm btn-danger" type="button" @click="remove(category)">删除</button>
          </div>
        </li>
      </ul>
    </div>

    <AppModal v-model="modalOpen" :title="editingId ? '编辑分类' : '新建分类'" width="400px">
      <div class="field">
        <label>分类名称</label>
        <input v-model="form.name" class="input" maxlength="30" placeholder="例如：考研资料" />
      </div>
      <div class="field mt-12">
        <label>排序（越小越靠前）</label>
        <input v-model="form.sort_order" class="input" inputmode="numeric" />
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
.loading { display: flex; flex-direction: column; gap: 8px; }
.list { display: flex; flex-direction: column; }
.item { display: flex; align-items: center; gap: 14px; padding: 12px 0; border-bottom: 1px solid var(--line); }
.item:last-child { border-bottom: none; }
.order {
  width: 26px; height: 26px; border-radius: 8px; flex: none;
  display: grid; place-items: center; background: #f1f3f7;
  color: var(--muted); font-size: 12px;
}
.info { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ops { display: flex; gap: 8px; }
</style>
