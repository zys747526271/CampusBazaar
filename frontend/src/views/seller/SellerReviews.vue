<script setup>
import { onMounted, reactive, ref } from 'vue'
import { sellerApi } from '@/api'
import { toastError, toastSuccess } from '@/composables/useToast'
import PageHeader from '@/components/ui/PageHeader.vue'
import AppImage from '@/components/ui/AppImage.vue'
import AppRating from '@/components/ui/AppRating.vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import { relativeTime } from '@/utils/format'

const loading = ref(true)
const items = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const unreplied = ref(false)
const replyOpen = ref(false)
const replyTarget = ref(null)
const replyText = ref('')
const replyBusy = ref(false)

const load = async (next = 1) => {
  loading.value = true
  try {
    const data = await sellerApi.comments({ page: next, per_page: 10, unreplied: unreplied.value ? 1 : undefined })
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

const toggleFilter = () => {
  unreplied.value = !unreplied.value
  load(1)
}

const openReply = (comment) => {
  replyTarget.value = comment
  replyText.value = comment.seller_reply || ''
  replyOpen.value = true
}

const submitReply = async () => {
  if (!replyText.value.trim()) {
    toastError('请填写回复内容')
    return
  }
  replyBusy.value = true
  try {
    await sellerApi.replyComment(replyTarget.value.id, replyText.value.trim())
    toastSuccess('回复成功')
    replyOpen.value = false
    load(page.value)
  } catch (error) {
    toastError(error.message)
  } finally {
    replyBusy.value = false
  }
}

onMounted(() => load(1))
</script>

<template>
  <div class="seller-reviews">
    <PageHeader title="商品评价" subtitle="及时回复评价，能明显提升买家的下单信心">
      <template #actions>
        <button class="btn btn-sm" :class="{ 'btn-ghost': unreplied }" type="button" @click="toggleFilter">
          {{ unreplied ? '查看全部评价' : '只看未回复' }}
        </button>
      </template>
    </PageHeader>

    <div class="panel">
      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 3" :key="i" :h="100" radius="10px" />
      </div>

      <AppEmpty
        v-else-if="!items.length"
        icon="message"
        title="还没有评价"
        description="完成交易后买家可以评价，回复评价能积累口碑"
        compact
      />

      <ul v-else class="list">
        <li v-for="comment in items" :key="comment.id" class="item">
          <div class="head">
            <span class="avatar">{{ (comment.user?.nickname || '同').slice(0, 1) }}</span>
            <div class="who">
              <strong>{{ comment.user?.nickname || '匿名同学' }}</strong>
              <div class="meta">
                <AppRating :model-value="comment.rating" :size="12" readonly />
                <span class="text-xs text-muted">{{ relativeTime(comment.created_at) }}</span>
              </div>
            </div>
            <div v-if="comment.product" class="product">
              <AppImage :src="comment.product.cover_image" :alt="comment.product.name" radius="6px" class="p-img" />
              <RouterLink :to="`/products/${comment.product.id}`" class="p-name ellipsis">{{ comment.product.name }}</RouterLink>
            </div>
          </div>

          <p class="content">{{ comment.content || '该同学没有填写文字评价' }}</p>
          <div v-if="comment.images?.length" class="images">
            <AppImage v-for="(image, index) in comment.images" :key="index" :src="image" radius="8px" />
          </div>

          <div v-if="comment.seller_reply" class="reply">
            <strong>我的回复：</strong>{{ comment.seller_reply }}
          </div>

          <div class="foot">
            <span class="text-xs text-muted">有用 {{ comment.like_count }}</span>
            <button class="btn btn-sm" type="button" @click="openReply(comment)">
              {{ comment.seller_reply ? '修改回复' : '回复评价' }}
            </button>
          </div>
        </li>
      </ul>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="10" @change="load" />
    </div>

    <AppModal v-model="replyOpen" title="回复评价" width="440px">
      <p v-if="replyTarget" class="quote">{{ replyTarget.content || '（无文字评价）' }}</p>
      <div class="field mt-12">
        <label>我的回复</label>
        <textarea v-model="replyText" class="textarea" maxlength="300" placeholder="例如：谢谢支持，有问题随时联系我" />
      </div>
      <template #footer>
        <button class="btn" type="button" @click="replyOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="replyBusy" @click="submitReply">
          {{ replyBusy ? '提交中…' : '发布回复' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.loading { display: flex; flex-direction: column; gap: 10px; }
.list { display: flex; flex-direction: column; }
.item { padding: 16px 0; border-bottom: 1px solid var(--line); }
.item:last-child { border-bottom: none; }
.head { display: flex; align-items: center; gap: 10px; }
.avatar {
  width: 34px; height: 34px; border-radius: 50%; flex: none;
  display: grid; place-items: center; font-size: 12px; font-weight: 700;
  background: #eef1f6; color: var(--ink-2);
}
.who { display: flex; flex-direction: column; gap: 2px; }
.meta { display: flex; align-items: center; gap: 8px; }
.product { margin-left: auto; display: flex; align-items: center; gap: 8px; max-width: 220px; }
.p-img { width: 30px; flex: none; }
.p-name { font-size: 12px; color: var(--muted); }
.p-name:hover { color: var(--brand); }

.content { margin-top: 10px; color: var(--ink-2); line-height: 1.75; }
.images { display: flex; gap: 8px; margin-top: 8px; }
.images > * { width: 76px; }
.reply { margin-top: 10px; background: #fafbfc; border-radius: 8px; padding: 8px 10px; font-size: 12.5px; color: var(--ink-2); }
.reply strong { color: var(--brand); font-weight: 500; }
.foot { display: flex; align-items: center; justify-content: space-between; margin-top: 10px; }
.quote { background: #fafbfc; border-radius: 8px; padding: 10px 12px; color: var(--muted); font-size: 13px; }
</style>
