<template>
  <div class="product-list-page">
    <div class="page-header">
      <h1>{{ search ? `搜索：${search}` : '全部商品' }}</h1>
      <span class="count" v-if="total">共 {{ total }} 件好物</span>
    </div>

    <div class="filter-bar">
      <el-select v-model="tagId" placeholder="全部分类" clearable @change="changeCategory" class="filter-select">
        <el-option v-for="tag in tags" :key="tag.id" :label="tag.name" :value="tag.id" />
      </el-select>
      <el-select v-model="sortBy" @change="changeSort" class="filter-select">
        <el-option label="最新上架" value="created_at" />
        <el-option label="价格从低到高" value="price_asc" />
        <el-option label="价格从高到低" value="price_desc" />
        <el-option label="最多浏览" value="views" />
      </el-select>
    </div>

    <div v-loading="loading">
      <el-row :gutter="20" v-if="products.length">
        <el-col :xs="12" :sm="8" :md="6" :lg="5" v-for="p in products" :key="p.id">
          <product-card :product="p" />
        </el-col>
      </el-row>
      <el-empty v-else-if="!loading" description="暂无商品，换个条件试试吧" />
    </div>

    <div class="pagination" v-if="total > pageSize">
      <el-pagination background layout="prev, pager, next" :total="total" :page-size="pageSize"
        v-model:current-page="page" @current-change="loadProducts" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/utils/api'
import ProductCard from '@/components/product/ProductCard.vue'

const route = useRoute()
const router = useRouter()
const products = ref([])
const tags = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const loading = ref(false)
const tagId = ref(null)
const sortBy = ref('created_at')
const search = computed(() => route.query.search || '')
const routeTagId = computed(() => route.query.tag_id ? Number(route.query.tag_id) : null)
const routeSort = computed(() => route.query.sort || '')

const applyRouteQuery = () => {
  if (routeTagId.value) tagId.value = routeTagId.value
  if (routeSort.value === 'hot') { sortBy.value = 'views' }
  else if (routeSort.value === 'recommended') { sortBy.value = 'created_at' }
  else if (routeSort.value) { sortBy.value = routeSort.value }
}

const changeCategory = (value) => {
  tagId.value = value
  page.value = 1
  const query = { ...route.query }
  if (value) query.tag_id = String(value)
  else delete query.tag_id
  router.replace({ path: '/products', query })
  loadProducts()
}

const changeSort = () => {
  page.value = 1
  const query = { ...route.query }
  if (routeSort.value) query.sort = sortBy.value === 'views' ? 'hot' : sortBy.value
  router.replace({ path: '/products', query })
  loadProducts()
}

const loadProducts = async () => {
  loading.value = true
  try {
    const params = { page: page.value, per_page: pageSize, search: search.value || undefined }
    if (tagId.value) params.tag_id = tagId.value
    if (sortBy.value === 'price_asc') { params.sort_by = 'price'; params.order = 'asc' }
    else if (sortBy.value === 'price_desc') { params.sort_by = 'price'; params.order = 'desc' }
    else if (sortBy.value === 'views') { params.sort_by = 'views'; params.order = 'desc' }
    else { params.sort_by = 'created_at'; params.order = 'desc' }
    const resp = await api.products.getList(params)
    products.value = resp.data?.items || []
    total.value = resp.data?.total || 0
  } catch (e) {
    products.value = []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  applyRouteQuery()
  try {
    const resp = await api.tags.getList({ per_page: 100 })
    tags.value = resp.data?.items || []
  } catch (e) { /* 分类加载失败不影响商品展示 */ }
  loadProducts()
})

watch(() => [route.query.search, route.query.tag_id, route.query.sort], () => {
  applyRouteQuery()
  page.value = 1
  loadProducts()
})
</script>

<style scoped>
.product-list-page { min-height: 60vh; }
.page-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 18px; }
.page-header h1 { font-size: 24px; color: #303133; }
.page-header .count { color: #909399; font-size: 14px; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 20px; }
.filter-select { width: 180px; }
.pagination { display: flex; justify-content: center; margin-top: 30px; }
</style>
