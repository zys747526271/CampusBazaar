<script setup>
import { onMounted, reactive, ref } from 'vue'
import { adminApiClient, uploadApi } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppModal from '@/components/ui/AppModal.vue'
import AppImage from '@/components/ui/AppImage.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'

const loading = ref(true)
const items = ref([])
const modalOpen = ref(false)
const editingId = ref(0)
const saving = ref(false)
const uploading = ref(false)

const form = reactive({ title: '', subtitle: '', image_url: '', link_url: '', sort_order: 0, is_active: true })

const load = async () => {
  loading.value = true
  try {
    const data = await adminApiClient.banners()
    items.value = data.items || []
  } catch (error) {
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  editingId.value = 0
  Object.assign(form, { title: '', subtitle: '', image_url: '', link_url: '/products', sort_order: items.value.length + 1, is_active: true })
  modalOpen.value = true
}

const openEdit = (banner) => {
  editingId.value = banner.id
  Object.assign(form, {
    title: banner.title,
    subtitle: banner.subtitle || '',
    image_url: banner.image_url,
    link_url: banner.link_url || '',
    sort_order: banner.sort_order,
    is_active: banner.is_active
  })
  modalOpen.value = true
}

const pickImage = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const data = await uploadApi.image(file)
    form.image_url = data.url
    toastSuccess('图片已上传')
  } catch (error) {
    toastError(error.message)
  } finally {
    uploading.value = false
    event.target.value = ''
  }
}

const save = async () => {
  if (!form.title.trim()) {
    toastError('请填写轮播标题')
    return
  }
  if (!form.image_url) {
    toastError('请上传轮播图片')
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      subtitle: form.subtitle.trim(),
      image_url: form.image_url,
      link_url: form.link_url.trim(),
      sort_order: Number(form.sort_order) || 0,
      is_active: form.is_active
    }
    if (editingId.value) await adminApiClient.updateBanner(editingId.value, payload)
    else await adminApiClient.createBanner(payload)
    toastSuccess('轮播已保存')
    modalOpen.value = false
    load()
  } catch (error) {
    toastError(error.message)
  } finally {
    saving.value = false
  }
}

const remove = async (banner) => {
  const ok = await confirmAction({
    title: '删除轮播',
    message: `确定删除「${banner.title}」吗？首页将不再展示。`,
    confirmText: '删除'
  })
  if (!ok) return
  try {
    await adminApiClient.deleteBanner(banner.id)
    toastSuccess('轮播已删除')
    load()
  } catch (error) {
    toastError(error.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="admin-banners">
    <header class="head">
      <div>
        <h1>首页轮播</h1>
        <p class="text-sm text-muted">建议尺寸 1200×420，按排序值从小到大展示</p>
      </div>
      <button class="btn btn-primary btn-sm" type="button" @click="openCreate">
        <AppIcon name="plus" :size="14" /> 新增轮播
      </button>
    </header>

    <div v-if="loading" class="loading">
      <SkeletonBlock v-for="i in 3" :key="i" :h="140" radius="12px" />
    </div>

    <div v-else-if="!items.length" class="panel">
      <AppEmpty icon="image" title="还没有轮播图" description="上传一张图片，为首页增加活动氛围">
        <button class="btn btn-primary btn-sm" type="button" @click="openCreate">新增轮播</button>
      </AppEmpty>
    </div>

    <div v-else class="grid">
      <article v-for="banner in items" :key="banner.id" class="banner-card">
        <div class="cover">
          <AppImage :src="banner.image_url" :alt="banner.title" :ratio="'1200 / 420'" radius="10px" />
          <span class="tag" :class="banner.is_active ? 'tag-ok' : ''">{{ banner.is_active ? '展示中' : '已停用' }}</span>
        </div>
        <div class="body">
          <strong>{{ banner.title }}</strong>
          <p class="text-xs text-muted">{{ banner.subtitle || '无副标题' }} · 排序 {{ banner.sort_order }}</p>
          <p class="text-xs text-muted ellipsis">跳转：{{ banner.link_url || '无' }}</p>
        </div>
        <div class="ops">
          <button class="btn btn-sm" type="button" @click="openEdit(banner)">编辑</button>
          <button class="btn btn-sm btn-danger" type="button" @click="remove(banner)">删除</button>
        </div>
      </article>
    </div>

    <AppModal v-model="modalOpen" :title="editingId ? '编辑轮播' : '新增轮播'" width="520px">
      <div class="field">
        <label>标题</label>
        <input v-model="form.title" class="input" maxlength="60" placeholder="例如：毕业季闲置清仓" />
      </div>
      <div class="field mt-12">
        <label>副标题（选填）</label>
        <input v-model="form.subtitle" class="input" maxlength="120" placeholder="例如：教材 / 数码 / 宿舍神器" />
      </div>
      <div class="field mt-12">
        <label>图片</label>
        <div class="upload-row">
          <AppImage v-if="form.image_url" :src="form.image_url" :alt="form.title" :ratio="'1200 / 420'" radius="8px" class="preview" />
          <label class="uploader">
            <AppIcon :name="uploading ? 'refresh' : 'upload'" :size="18" />
            {{ uploading ? '上传中…' : '上传图片' }}
            <input type="file" accept="image/jpeg,image/png,image/webp" hidden :disabled="uploading" @change="pickImage" />
          </label>
        </div>
      </div>
      <div class="grid-2 mt-12">
        <div class="field">
          <label>跳转链接</label>
          <input v-model="form.link_url" class="input" maxlength="255" placeholder="/products?tag_id=1" />
        </div>
        <div class="field">
          <label>排序</label>
          <input v-model="form.sort_order" class="input" inputmode="numeric" />
        </div>
      </div>
      <label class="check mt-12"><input v-model="form.is_active" type="checkbox" /> 在首页展示</label>
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
.loading { display: flex; flex-direction: column; gap: 12px; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.banner-card { background: #fff; border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.cover { position: relative; }
.cover .tag { position: absolute; left: 10px; top: 10px; background: #fff; }
.body { padding: 12px 14px; display: flex; flex-direction: column; gap: 3px; }
.ops { display: flex; gap: 8px; padding: 0 14px 14px; }

.upload-row { display: flex; gap: 12px; align-items: flex-start; }
.preview { width: 220px; flex: none; border: 1px solid var(--line); }
.uploader {
  display: inline-flex; align-items: center; gap: 7px;
  border: 1px dashed var(--line-strong); border-radius: 8px;
  padding: 10px 16px; color: var(--muted); font-size: 13px; cursor: pointer;
}
.uploader:hover { border-color: var(--brand); color: var(--brand); }
.grid-2 { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; }
.check { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: var(--ink-2); }
.check input { accent-color: var(--brand); }
@media (max-width: 760px) { .grid { grid-template-columns: 1fr; } }
</style>
