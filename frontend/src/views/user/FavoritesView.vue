<script setup>
import { onMounted, ref } from 'vue'
import { favoriteApi } from '@/api'
import { toastError, toastSuccess } from '@/composables/useToast'
import ProductGrid from '@/components/product/ProductGrid.vue'
import AppPagination from '@/components/ui/AppPagination.vue'

const loading = ref(true)
const items = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)

const load = async (next = 1) => {
  loading.value = true
  try {
    const data = await favoriteApi.list({ page: next, per_page: 12 })
    items.value = data.items || []
    total.value = data.total || 0
    pages.value = data.pages || 0
    page.value = data.page || 1
  } catch (error) {
    toastError(error.message)
    items.value = []
  } finally {
    loading.value = false
  }
}

const removeFavorite = async (product) => {
  try {
    await favoriteApi.remove(product.id)
    toastSuccess('已取消收藏')
    load(page.value)
  } catch (error) {
    toastError(error.message)
  }
}

onMounted(() => load(1))
</script>

<template>
  <div class="favorites">
    <div class="panel">
      <header class="head">
        <div>
          <h1>我的收藏</h1>
          <p class="text-sm text-muted">共收藏 {{ total }} 件商品，降价和新上架一目了然</p>
        </div>
        <RouterLink to="/products" class="btn btn-sm">发现更多</RouterLink>
      </header>

      <ProductGrid
        :products="items"
        :loading="loading"
        :skeleton-count="8"
        :columns="4"
        :show-favorite="true"
        :favorited="true"
        empty-title="还没有收藏任何商品"
        empty-description="在商品详情页点击爱心即可收藏"
        @favorite="removeFavorite"
      >
        <template #empty-action>
          <RouterLink to="/products" class="btn btn-primary btn-sm">去逛逛</RouterLink>
        </template>
      </ProductGrid>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="12" @change="load" />
    </div>
  </div>
</template>

<style scoped>
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.head h1 { font-size: 21px; letter-spacing: -.3px; }
</style>
