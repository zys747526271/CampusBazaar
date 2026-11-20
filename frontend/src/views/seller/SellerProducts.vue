<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { sellerApi } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import PageHeader from '@/components/ui/PageHeader.vue'
import AppTabs from '@/components/ui/AppTabs.vue'
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
const keyword = ref('')
const status = ref(route.query.status || '')
const busyId = ref(0)

const tabs = computed(() => [
  { label: '全部', value: '' },
  { label: '待审核', value: '待审核' },
  { label: '已通过', value: '已通过' },
  { label: '已下架', value: '已下架' }
])

const load = async (next = 1) => {
  loading.value = true
  try {
    const data = await sellerApi.products({
      page: next,
      per_page: 10,
      status: status.value || undefined,
      keyword: keyword.value || undefined
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

const changeTab = (value) => {
  status.value = value
  router.replace({ path: '/seller/products', query: value ? { status: value } : {} })
  load(1)
}

const search = () => load(1)

const toggle = async (product) => {
  busyId.value = product.id
  try {
    const data = await sellerApi.toggleProduct(product.id)
    toastSuccess(product.is_available ? '商品已下架' : '商品已上架')
    Object.assign(product, data)
  } catch (error) {
    toastError(error.message)
  } finally {
    busyId.value = 0
  }
}

const remove = async (product) => {
  const ok = await confirmAction({
    title: '删除商品',
    message: `确定删除《${product.name}》吗？删除后买家将无法看到该商品（历史订单保留）。`,
    confirmText: '删除商品'
  })
  if (!ok) return
  busyId.value = product.id
  try {
    await sellerApi.deleteProduct(product.id)
    toastSuccess('商品已删除')
    load(page.value)
  } catch (error) {
    toastError(error.message)
  } finally {
    busyId.value = 0
  }
}

onMounted(() => load(1))
</script>

<template>
  <div class="seller-products">
    <PageHeader title="我的商品" subtitle="管理在售、待审核与已下架的商品">
      <template #actions>
        <RouterLink to="/seller/products/new" class="btn btn-primary btn-sm">
          <AppIcon name="plus" :size="14" /> 发布商品
        </RouterLink>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="toolbar">
        <AppTabs :items="tabs" :model-value="status" @change="changeTab" />
        <form class="search" @submit.prevent="search">
          <AppIcon name="search" :size="15" />
          <input v-model="keyword" placeholder="搜索商品名称" maxlength="30" />
          <button type="submit" class="btn btn-sm">搜索</button>
        </form>
      </div>

      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 5" :key="i" :h="52" radius="8px" />
      </div>

      <AppEmpty
        v-else-if="!items.length"
        icon="package"
        title="还没有商品"
        description="发布你的第一件闲置，让它找到需要它的同学"
      >
        <RouterLink to="/seller/products/new" class="btn btn-primary btn-sm">发布商品</RouterLink>
      </AppEmpty>

      <table v-else class="table">
        <thead>
          <tr>
            <th>商品</th>
            <th>价格</th>
            <th>库存 / 已售</th>
            <th>浏览</th>
            <th>评价</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="product in items" :key="product.id">
            <td>
              <div class="product-cell">
                <AppImage :src="product.cover_image" :alt="product.name" radius="8px" class="thumb" />
                <div class="p-info">
                  <RouterLink :to="`/products/${product.id}`" class="p-name clamp-2">{{ product.name }}</RouterLink>
                  <span class="text-xs text-muted">{{ product.tag?.name || '未分类' }} · {{ product.condition }}</span>
                </div>
              </div>
            </td>
            <td><span class="price price-sm"><span class="unit">¥</span>{{ money(product.price) }}</span></td>
            <td>
              <span :class="{ 'text-danger': product.quantity <= 0 }">{{ product.quantity }}</span>
              <span class="text-muted"> / {{ product.sales }}</span>
            </td>
            <td class="text-muted">{{ product.views }}</td>
            <td class="text-muted">{{ product.comment_count }}</td>
            <td>
              <StatusTag :status="product.status" kind="product" />
              <span v-if="product.status === '已通过' && !product.is_available" class="tag ml-6">已售罄</span>
              <p v-if="product.reject_reason" class="text-xs text-danger mt-8">{{ product.reject_reason }}</p>
            </td>
            <td>
              <div class="table-actions">
                <RouterLink :to="`/seller/products/${product.id}/edit`" class="btn btn-sm">编辑</RouterLink>
                <button class="btn btn-sm" type="button" :disabled="busyId === product.id" @click="toggle(product)">
                  {{ product.status === '已通过' && product.is_available ? '下架' : '上架' }}
                </button>
                <button class="btn btn-sm btn-danger" type="button" :disabled="busyId === product.id" @click="remove(product)">
                  删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="10" @change="load" />
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }
.search { display: flex; align-items: center; gap: 6px; border: 1px solid var(--line-strong); border-radius: 8px; padding: 3px 4px 3px 10px; color: var(--muted); }
.search input { border: none; outline: none; height: 28px; width: 160px; font-size: 13px; }
.loading { display: flex; flex-direction: column; gap: 8px; padding-top: 8px; }

.product-cell { display: flex; align-items: center; gap: 10px; min-width: 220px; }
.thumb { width: 48px; flex: none; }
.p-info { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.p-name { font-size: 13px; }
.p-name:hover { color: var(--brand); }
.ml-6 { margin-left: 6px; }
</style>
