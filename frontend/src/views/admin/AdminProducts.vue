<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminApiClient, saveBlob } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppModal from '@/components/ui/AppModal.vue'
import AppImage from '@/components/ui/AppImage.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusTag from '@/components/ui/StatusTag.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { dateOnly, money } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const items = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const keyword = ref(route.query.keyword || '')
const status = ref(route.query.status || '')
const tagId = ref(route.query.tag_id || '')
const sellerId = ref(route.query.seller_id || '')
const tags = ref([])
const selected = ref([])

const statusOpen = ref(false)
const statusTarget = ref(null)
const statusForm = reactive({ status: '已通过', reason: '' })
const statusBusy = ref(false)
const batchReason = ref('')

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '待审核', value: '待审核' },
  { label: '已通过', value: '已通过' },
  { label: '已下架', value: '已下架' }
]

const allChecked = computed(() => items.value.length > 0 && selected.value.length === items.value.length)

const exportCsv = async () => {
  try {
    const res = await adminApiClient.exportCsv('products')
    saveBlob(res.data, `campus-products-${new Date().toISOString().slice(0, 10)}.csv`)
    toastSuccess('已导出 CSV')
  } catch (error) {
    toastError(error.message)
  }
}

const load = async (next = 1) => {
  loading.value = true
  try {
    const data = await adminApiClient.products({
      page: next,
      per_page: 15,
      keyword: keyword.value || undefined,
      status: status.value || undefined,
      tag_id: tagId.value || undefined,
      seller_id: sellerId.value || undefined
    })
    items.value = data.items || []
    total.value = data.total || 0
    pages.value = data.pages || 0
    page.value = data.page || 1
    selected.value = []
  } catch (error) {
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

const search = () => {
  const query = {}
  if (keyword.value) query.keyword = keyword.value
  if (status.value) query.status = status.value
  if (tagId.value) query.tag_id = tagId.value
  if (sellerId.value) query.seller_id = sellerId.value
  router.replace({ path: '/admin/products', query })
  load(1)
}

const clearSeller = () => {
  sellerId.value = ''
  search()
}

const toggleAll = () => {
  selected.value = allChecked.value ? [] : items.value.map((item) => item.id)
}

const toggleOne = (id) => {
  const index = selected.value.indexOf(id)
  if (index >= 0) selected.value.splice(index, 1)
  else selected.value.push(id)
}

const openStatus = (product, next) => {
  statusTarget.value = product
  statusForm.status = next
  statusForm.reason = ''
  statusOpen.value = true
}

const submitStatus = async () => {
  if (statusForm.status === '已下架' && !statusForm.reason.trim()) {
    toastError('下架必须填写原因')
    return
  }
  statusBusy.value = true
  try {
    await adminApiClient.updateProductStatus(statusTarget.value.id, {
      status: statusForm.status,
      reason: statusForm.reason.trim()
    })
    toastSuccess('操作成功')
    statusOpen.value = false
    load(page.value)
  } catch (error) {
    toastError(error.message)
  } finally {
    statusBusy.value = false
  }
}

const batchStatus = async (next) => {
  if (!selected.value.length) return
  if (next === '已下架' && !batchReason.value.trim()) {
    toastError('批量下架需要填写原因')
    return
  }
  const ok = await confirmAction({
    title: next === '已通过' ? '批量通过审核' : '批量下架',
    message: `将对选中的 ${selected.value.length} 件商品执行「${next}」。`,
    confirmText: '确认执行'
  })
  if (!ok) return
  try {
    const data = await adminApiClient.batchProductStatus({
      ids: selected.value,
      status: next,
      reason: batchReason.value.trim() || '管理员批量操作'
    })
    toastSuccess(`处理完成：成功 ${data.success_count} 件`)
    batchReason.value = ''
    load(page.value)
  } catch (error) {
    toastError(error.message)
  }
}

const toggleFeature = async (product) => {
  try {
    await adminApiClient.featureProduct(product.id, !product.is_featured)
    product.is_featured = !product.is_featured
    toastSuccess(product.is_featured ? '已加入推荐位' : '已取消推荐')
  } catch (error) {
    toastError(error.message)
  }
}

onMounted(async () => {
  try {
    const data = await adminApiClient.productTags()
    tags.value = data.items || []
  } catch (error) {
    tags.value = []
  }
  load(1)
})
</script>

<template>
  <div class="admin-products">
    <header class="head">
      <div>
        <h1>商品管理</h1>
        <p class="text-sm text-muted">共 {{ total }} 件商品 · 待审核商品需人工通过后才会展示</p>
      </div>
      <div class="toolbar">
        <form class="search" @submit.prevent="search">
          <AppIcon name="search" :size="15" />
          <input v-model="keyword" placeholder="搜索商品名称 / 描述" maxlength="40" />
        </form>
        <button class="btn btn-sm" type="button" @click="exportCsv">导出 CSV</button>
        <select v-model="status" class="select input-sm" @change="search">
          <option v-for="option in statusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
        <select v-model="tagId" class="select input-sm" @change="search">
          <option value="">全部分类</option>
          <option v-for="tag in tags" :key="tag.id" :value="tag.id">{{ tag.name }}</option>
        </select>
      </div>
    </header>

    <div v-if="sellerId" class="alert mb-12">
      <AppIcon name="filter" :size="14" />
      当前仅显示商家 ID {{ sellerId }} 的商品
      <button class="btn-text" type="button" style="margin-left: auto" @click="clearSeller">清除筛选</button>
    </div>

    <div v-if="selected.length" class="batch-bar">
      <span>已选 {{ selected.length }} 件</span>
      <input v-model="batchReason" class="input input-sm batch-input" placeholder="批量下架原因（下架时必填）" maxlength="100" />
      <button class="btn btn-sm btn-primary" type="button" @click="batchStatus('已通过')">批量通过</button>
      <button class="btn btn-sm btn-danger" type="button" @click="batchStatus('已下架')">批量下架</button>
      <button class="btn btn-sm" type="button" @click="selected = []">取消选择</button>
    </div>

    <div class="panel">
      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 6" :key="i" :h="50" radius="8px" />
      </div>

      <AppEmpty v-else-if="!items.length" icon="package" title="没有匹配的商品" compact />

      <table v-else class="table">
        <thead>
          <tr>
            <th class="check-col"><input type="checkbox" :checked="allChecked" @change="toggleAll" /></th>
            <th>商品</th>
            <th>商家</th>
            <th>价格 / 库存</th>
            <th>状态</th>
            <th>推荐</th>
            <th>发布</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="product in items" :key="product.id">
            <td class="check-col"><input type="checkbox" :checked="selected.includes(product.id)" @change="toggleOne(product.id)" /></td>
            <td>
              <div class="cell">
                <AppImage :src="product.cover_image" :alt="product.name" radius="6px" class="thumb" />
                <div class="p-info">
                  <RouterLink :to="`/products/${product.id}`" target="_blank" class="p-name clamp-2">{{ product.name }}</RouterLink>
                  <span class="text-xs text-muted">{{ product.tag?.name || '未分类' }} · {{ product.condition }}</span>
                </div>
              </div>
            </td>
            <td>{{ product.seller?.nickname || '—' }}</td>
            <td>¥{{ money(product.price) }} · {{ product.quantity }}</td>
            <td>
              <StatusTag :status="product.status" kind="product" />
              <p v-if="product.reject_reason" class="text-xs text-danger mt-4">{{ product.reject_reason }}</p>
            </td>
            <td>
              <button class="star-btn" :class="{ on: product.is_featured }" type="button" @click="toggleFeature(product)">
                <AppIcon name="star" :size="15" :filled="product.is_featured" />
              </button>
            </td>
            <td class="text-muted">{{ dateOnly(product.created_at) }}</td>
            <td>
              <div class="table-actions">
                <button v-if="product.status !== '已通过'" class="btn btn-sm btn-primary" type="button" @click="openStatus(product, '已通过')">通过</button>
                <button v-if="product.status !== '已下架'" class="btn btn-sm btn-danger" type="button" @click="openStatus(product, '已下架')">下架</button>
                <button v-if="product.status === '已下架'" class="btn btn-sm" type="button" @click="openStatus(product, '待审核')">转待审</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="15" @change="load" />
    </div>

    <AppModal v-model="statusOpen" :title="`商品${statusForm.status}`" width="440px">
      <p class="text-sm">商品：<strong>{{ statusTarget?.name }}</strong></p>
      <div class="field mt-12">
        <label>{{ statusForm.status === '已下架' ? '下架原因（必填，会通知卖家）' : '备注（选填）' }}</label>
        <textarea v-model="statusForm.reason" class="textarea" maxlength="200" placeholder="例如：含联系方式引流 / 疑似违禁物品" />
      </div>
      <template #footer>
        <button class="btn" type="button" @click="statusOpen = false">取消</button>
        <button class="btn" :class="statusForm.status === '已下架' ? 'btn-danger' : 'btn-primary'" type="button" :disabled="statusBusy" @click="submitStatus">
          {{ statusBusy ? '处理中…' : '确认' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.head h1 { font-size: 22px; }
.toolbar { display: flex; gap: 8px; flex-wrap: wrap; }
.search { display: flex; align-items: center; gap: 6px; border: 1px solid var(--line-strong); border-radius: 8px; padding: 3px 10px; background: #fff; color: var(--muted); }
.search input { border: none; outline: none; height: 28px; width: 190px; font-size: 13px; }
.loading { display: flex; flex-direction: column; gap: 8px; }

.batch-bar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  background: #fff8f3; border: 1px solid #ffd9c4; border-radius: 10px;
  padding: 10px 14px; margin-bottom: 12px; font-size: 13px; color: #8a4a22;
}
.batch-input { width: 240px; }

.check-col { width: 36px; }
.check-col input { accent-color: var(--brand); }
.cell { display: flex; align-items: center; gap: 10px; min-width: 220px; }
.thumb { width: 44px; flex: none; }
.p-info { min-width: 0; }
.p-name { font-size: 13px; }
.p-name:hover { color: var(--brand); }
.mt-4 { margin-top: 4px; }

.star-btn { border: none; background: none; color: #d8dde5; padding: 2px; }
.star-btn.on { color: #ff9f0a; }
</style>
