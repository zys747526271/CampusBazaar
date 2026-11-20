<script setup>
import { onMounted, ref } from 'vue'
import { historyApi } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
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
    const data = await historyApi.list({ page: next, per_page: 12 })
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

const clearAll = async () => {
  const ok = await confirmAction({
    title: '清空浏览记录',
    message: '清空后将无法恢复，确定继续吗？',
    confirmText: '清空'
  })
  if (!ok) return
  try {
    await historyApi.clear()
    toastSuccess('浏览记录已清空')
    load(1)
  } catch (error) {
    toastError(error.message)
  }
}

onMounted(() => load(1))
</script>

<template>
  <div class="history">
    <div class="panel">
      <header class="head">
        <div>
          <h1>浏览记录</h1>
          <p class="text-sm text-muted">最近看过的商品，最多保留 100 条</p>
        </div>
        <button v-if="total" class="btn btn-sm btn-danger" type="button" @click="clearAll">清空记录</button>
      </header>

      <ProductGrid
        :products="items"
        :loading="loading"
        :skeleton-count="8"
        :columns="4"
        empty-title="还没有浏览记录"
        empty-description="看过的商品会自动出现在这里，方便回头再找"
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
