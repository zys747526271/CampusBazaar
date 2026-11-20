<script setup>
import { onMounted, reactive, ref } from 'vue'
import { adminApiClient } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppModal from '@/components/ui/AppModal.vue'
import AppImage from '@/components/ui/AppImage.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import AppRating from '@/components/ui/AppRating.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { dateTime } from '@/utils/format'

const loading = ref(true)
const items = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const keyword = ref('')
const visibility = ref('')

const actionOpen = ref(false)
const target = ref(null)
const actionForm = reactive({ hidden: true, reason: '' })
const busy = ref(false)

const visibilityOptions = [
  { value: '', label: '全部评价' },
  { value: 'visible', label: '正常展示' },
  { value: 'hidden', label: '已隐藏' }
]

const load = async (next = 1) => {
  loading.value = true
  try {
    const data = await adminApiClient.comments({
      page: next,
      per_page: 12,
      keyword: keyword.value || undefined,
      visibility: visibility.value || undefined
    })
    items.value = data.items || []
    total.value = data.total || 0
    pages.value = data.pages || 0
    page.value = data.page || 1
  } catch (error) {
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

const openAction = (comment, hidden) => {
  target.value = comment
  actionForm.hidden = hidden
  actionForm.reason = ''
  actionOpen.value = true
}

const submit = async () => {
  if (actionForm.hidden && !actionForm.reason.trim()) {
    toastError('隐藏评价请填写原因，便于申诉时说明')
    return
  }
  busy.value = true
  try {
    await adminApiClient.commentVisibility(target.value.id, {
      hidden: actionForm.hidden,
      reason: actionForm.reason.trim()
    })
    toastSuccess(actionForm.hidden ? '评价已隐藏' : '评价已恢复')
    actionOpen.value = false
    load(page.value)
  } catch (error) {
    toastError(error.message)
  } finally {
    busy.value = false
  }
}

const remove = async (comment) => {
  const ok = await confirmAction({
    title: '删除评价',
    message: '删除后数据保留但前台不再展示，确定删除吗？',
    confirmText: '删除评价'
  })
  if (!ok) return
  try {
    await adminApiClient.deleteComment(comment.id)
    toastSuccess('评价已删除')
    load(page.value)
  } catch (error) {
    toastError(error.message)
  }
}

onMounted(() => load(1))
</script>

<template>
  <div class="admin-comments">
    <header class="head">
      <div>
        <h1>评价管理</h1>
        <p class="text-sm text-muted">共 {{ total }} 条评价 · 隐藏后买家侧立即不可见</p>
      </div>
      <div class="toolbar">
        <form class="search" @submit.prevent="load(1)">
          <AppIcon name="search" :size="15" />
          <input v-model="keyword" placeholder="搜索评价内容 / 商品" maxlength="40" />
        </form>
        <select v-model="visibility" class="select input-sm" @change="load(1)">
          <option v-for="option in visibilityOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </div>
    </header>

    <div class="panel">
      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 4" :key="i" :h="80" radius="10px" />
      </div>

      <AppEmpty v-else-if="!items.length" icon="message" title="没有匹配的评价" compact />

      <ul v-else class="list">
        <li v-for="comment in items" :key="comment.id" class="item" :class="{ hidden: comment.is_hidden }">
          <div class="row">
            <span class="avatar">{{ (comment.user?.nickname || '匿').slice(0, 1) }}</span>
            <div class="who">
              <strong>{{ comment.user?.nickname || '匿名' }}</strong>
              <div class="meta">
                <AppRating :model-value="comment.rating" :size="12" readonly />
                <span class="text-xs text-muted">{{ dateTime(comment.created_at) }}</span>
              </div>
            </div>
            <div class="product">
              <AppImage :src="comment.product?.cover_image" :alt="comment.product?.name" radius="6px" class="p-img" />
              <span class="p-name ellipsis">{{ comment.product?.name || '商品已删除' }}</span>
            </div>
            <span class="tag" :class="comment.is_hidden ? 'tag-danger' : 'tag-ok'">{{ comment.is_hidden ? '已隐藏' : '正常' }}</span>
          </div>

          <p class="content">{{ comment.content || '（无文字评价）' }}</p>
          <div v-if="comment.seller_reply" class="reply">卖家回复：{{ comment.seller_reply }}</div>

          <div class="ops">
            <button class="btn btn-sm" :class="{ 'btn-primary': comment.is_hidden }" type="button" @click="openAction(comment, !comment.is_hidden)">
              {{ comment.is_hidden ? '恢复展示' : '隐藏评价' }}
            </button>
            <button class="btn btn-sm btn-danger" type="button" @click="remove(comment)">删除</button>
            <RouterLink v-if="comment.product" :to="`/products/${comment.product.id}`" target="_blank" class="btn btn-sm">
              查看商品
            </RouterLink>
          </div>
        </li>
      </ul>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="12" @change="load" />
    </div>

    <AppModal v-model="actionOpen" :title="actionForm.hidden ? '隐藏评价' : '恢复评价'" width="440px">
      <div class="alert" :class="actionForm.hidden ? 'alert-warn' : 'alert-ok'">
        <AppIcon :name="actionForm.hidden ? 'alert' : 'info'" :size="15" />
        <span v-if="actionForm.hidden">隐藏后该评价在商品详情页不再展示，数据保留用于申诉。</span>
        <span v-else>恢复后评价会重新展示在商品详情页。</span>
      </div>
      <p v-if="target" class="quote mt-12">{{ target.content || '（无文字评价）' }}</p>
      <div class="field mt-12">
        <label>处置原因</label>
        <textarea v-model="actionForm.reason" class="textarea" maxlength="200" placeholder="例如：评价含联系方式引流 / 辱骂他人" />
      </div>
      <template #footer>
        <button class="btn" type="button" @click="actionOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="busy" @click="submit">
          {{ busy ? '处理中…' : '确认' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.head h1 { font-size: 22px; }
.toolbar { display: flex; gap: 8px; flex-wrap: wrap; }
.search { display: flex; align-items: center; gap: 6px; border: 1px solid var(--line-strong); border-radius: 8px; padding: 3px 10px; background: #fff; color: var(--muted); }
.search input { border: none; outline: none; height: 28px; width: 190px; font-size: 13px; }
.loading { display: flex; flex-direction: column; gap: 10px; }

.list { display: flex; flex-direction: column; }
.item { padding: 14px 0; border-bottom: 1px solid var(--line); }
.item:last-child { border-bottom: none; }
.item.hidden { background: #fdf7f7; margin: 0 -22px; padding-inline: 22px; }
.row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.avatar {
  width: 32px; height: 32px; border-radius: 50%; flex: none;
  display: grid; place-items: center; font-size: 12px; font-weight: 700;
  background: #eef1f6; color: var(--ink-2);
}
.who { display: flex; flex-direction: column; gap: 1px; }
.meta { display: flex; align-items: center; gap: 8px; }
.product { display: flex; align-items: center; gap: 7px; margin-left: auto; max-width: 240px; }
.p-img { width: 28px; flex: none; }
.p-name { font-size: 12px; color: var(--muted); }
.content { margin-top: 8px; color: var(--ink-2); font-size: 13.5px; }
.reply { margin-top: 6px; font-size: 12.5px; color: var(--muted); background: #fafbfc; padding: 6px 10px; border-radius: 6px; }
.ops { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.quote { background: #fafbfc; border-radius: 8px; padding: 10px 12px; font-size: 13px; color: var(--muted); }
</style>
