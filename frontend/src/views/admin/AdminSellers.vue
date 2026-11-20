<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminApiClient } from '@/api'
import { toastError } from '@/composables/useToast'
import AppModal from '@/components/ui/AppModal.vue'
import AppImage from '@/components/ui/AppImage.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusTag from '@/components/ui/StatusTag.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { dateOnly, money } from '@/utils/format'

const router = useRouter()

const loading = ref(true)
const keyword = ref('')
const items = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)

const productsOpen = ref(false)
const currentSeller = ref(null)
const sellerProducts = ref([])
const productsLoading = ref(false)
const productKeyword = ref('')

const load = async (next = 1) => {
  loading.value = true
  try {
    const data = await adminApiClient.sellers({ page: next, per_page: 15, keyword: keyword.value || undefined })
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

const openProducts = async (seller) => {
  currentSeller.value = seller
  productsOpen.value = true
  productKeyword.value = ''
  await loadSellerProducts(1)
}

const loadSellerProducts = async (next = 1) => {
  productsLoading.value = true
  try {
    const data = await adminApiClient.sellerProducts(currentSeller.value.id, {
      page: next,
      per_page: 10,
      keyword: productKeyword.value || undefined
    })
    sellerProducts.value = data.items || []
  } catch (error) {
    toastError(error.message)
  } finally {
    productsLoading.value = false
  }
}

const goAudit = (seller) => {
  productsOpen.value = false
  router.push({ path: '/admin/products', query: { seller_id: seller.id } })
}

onMounted(() => load(1))
</script>

<template>
  <div class="admin-sellers">
    <header class="head">
      <div>
        <h1>商家管理</h1>
        <p class="text-sm text-muted">共 {{ total }} 位卖家 · 可按昵称或手机号检索</p>
      </div>
      <form class="search" @submit.prevent="load(1)">
        <AppIcon name="search" :size="15" />
        <input v-model="keyword" placeholder="搜索商家" maxlength="30" />
      </form>
    </header>

    <div class="panel">
      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 5" :key="i" :h="46" radius="8px" />
      </div>

      <AppEmpty v-else-if="!items.length" icon="shop" title="暂无商家" description="还没有用户开通卖家身份" compact />

      <table v-else class="table">
        <thead>
          <tr>
            <th>商家</th>
            <th>手机号</th>
            <th>商品</th>
            <th>订单 / 成交额</th>
            <th>开店时间</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="seller in items" :key="seller.id">
            <td>
              <div class="cell">
                <span class="avatar">{{ (seller.nickname || '店').slice(0, 1) }}</span>
                <div>
                  <p class="name">{{ seller.nickname }}</p>
                  <p class="text-xs text-muted">ID {{ seller.id }} · {{ seller.campus || '未填写校区' }}</p>
                </div>
              </div>
            </td>
            <td class="mono">{{ seller.phone }}</td>
            <td>{{ seller.product_count }} 件（在售 {{ seller.on_sale_count }}）</td>
            <td>{{ seller.order_count }} 单 / ¥{{ money(seller.gmv) }}</td>
            <td class="text-muted">{{ dateOnly(seller.seller_since) }}</td>
            <td>
              <span class="tag" :class="seller.is_banned ? 'tag-danger' : 'tag-ok'">{{ seller.is_banned ? '已封禁' : '正常' }}</span>
            </td>
            <td>
              <div class="table-actions">
                <button class="btn btn-sm" type="button" @click="openProducts(seller)">查看商品</button>
                <button class="btn btn-sm" type="button" @click="goAudit(seller)">商品审核</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="15" @change="load" />
    </div>

    <AppModal v-model="productsOpen" :title="`${currentSeller?.nickname || ''} 的商品`" width="720px">
      <form class="search mb-12" @submit.prevent="loadSellerProducts(1)">
        <AppIcon name="search" :size="15" />
        <input v-model="productKeyword" placeholder="搜索商品名称" maxlength="30" />
        <button class="btn btn-sm" type="submit">搜索</button>
      </form>

      <div v-if="productsLoading" class="loading">
        <SkeletonBlock v-for="i in 3" :key="i" :h="46" radius="8px" />
      </div>
      <AppEmpty v-else-if="!sellerProducts.length" icon="package" title="该商家暂无商品" compact />
      <table v-else class="table">
        <thead><tr><th>商品</th><th>价格</th><th>库存</th><th>状态</th></tr></thead>
        <tbody>
          <tr v-for="product in sellerProducts" :key="product.id">
            <td>
              <div class="cell">
                <AppImage :src="product.cover_image" :alt="product.name" radius="6px" class="thumb" />
                <span class="clamp-2 cell-name">{{ product.name }}</span>
              </div>
            </td>
            <td>¥{{ money(product.price) }}</td>
            <td>{{ product.quantity }}</td>
            <td><StatusTag :status="product.status" kind="product" /></td>
          </tr>
        </tbody>
      </table>
    </AppModal>
  </div>
</template>

<style scoped>
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.head h1 { font-size: 22px; }
.search { display: flex; align-items: center; gap: 6px; border: 1px solid var(--line-strong); border-radius: 8px; padding: 3px 10px; background: #fff; color: var(--muted); }
.search input { border: none; outline: none; height: 28px; width: 170px; font-size: 13px; }
.loading { display: flex; flex-direction: column; gap: 8px; }
.mono { font-family: var(--mono); font-size: 12px; color: var(--ink-2); }
.cell { display: flex; align-items: center; gap: 10px; min-width: 180px; }
.cell-name { font-size: 13px; }
.avatar {
  width: 34px; height: 34px; border-radius: 50%; flex: none;
  display: grid; place-items: center; font-size: 12px; font-weight: 700;
  background: linear-gradient(135deg, #ffe2d3, #ffc3a6); color: #a03c0d;
}
.name { font-size: 13.5px; }
.thumb { width: 40px; flex: none; }
</style>
