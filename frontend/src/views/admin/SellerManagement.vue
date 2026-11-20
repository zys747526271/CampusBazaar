<template>
  <div class="seller-admin-page">
    <div class="page-header">
      <h1>商家管理</h1>
      <el-input v-model="search" placeholder="搜索商家昵称 / 手机号" style="width:280px" clearable @keyup.enter="loadSellers" @clear="loadSellers">
        <template #append><el-button @click="loadSellers">搜索</el-button></template>
      </el-input>
    </div>

    <el-table :data="sellers" v-loading="loading" border style="width:100%">
      <el-table-column prop="nickname" label="商家" min-width="160" />
      <el-table-column prop="phone" label="手机号" width="140" />
      <el-table-column prop="product_count" label="商品数" width="100" />
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button size="small" type="primary" text @click="openProducts(row)">查看商品</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!sellers.length && !loading" description="暂无商家" />
    <div class="pagination" v-if="total > pageSize">
      <el-pagination background layout="prev, pager, next" :total="total" :page-size="pageSize"
        v-model:current-page="page" @current-change="loadSellers" />
    </div>

    <el-dialog v-model="dialogVisible" :title="`「${currentSeller?.nickname}」的商品`" width="800px">
      <el-input v-model="productSearch" placeholder="搜索该商家的商品名称" style="width:300px;margin-bottom:12px" clearable @keyup.enter="loadSellerProducts" @clear="loadSellerProducts">
        <template #append><el-button @click="loadSellerProducts">搜索</el-button></template>
      </el-input>
      <el-table :data="products" v-loading="productLoading" border>
        <el-table-column label="商品" min-width="220">
          <template #default="{ row }">
            <div class="product-cell">
              <el-image v-if="row.images?.length" :src="row.images[0]" fit="cover" class="thumb" />
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" width="100">
          <template #default="{ row }">¥{{ Number(row.price).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="quantity" label="库存" width="80" />
        <el-table-column prop="status" label="状态" width="100" />
      </el-table>
      <el-empty v-if="!products.length && !productLoading" description="该商家暂无商品" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const sellers = ref([])
const products = ref([])
const currentSeller = ref(null)
const search = ref('')
const productSearch = ref('')
const loading = ref(false)
const productLoading = ref(false)
const dialogVisible = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)

const loadSellers = async () => {
  loading.value = true
  try {
    const resp = await api.admin.getSellers({ page: page.value, per_page: pageSize, search: search.value })
    sellers.value = resp.data?.items || []
    total.value = resp.data?.total || 0
  } catch (e) { ElMessage.error('获取商家列表失败') }
  finally { loading.value = false }
}

const loadSellerProducts = async () => {
  if (!currentSeller.value) return
  productLoading.value = true
  try {
    const resp = await api.admin.getSellerProducts(currentSeller.value.id, { search: productSearch.value })
    products.value = resp.data?.items || []
  } catch (e) { ElMessage.error('获取商品失败') }
  finally { productLoading.value = false }
}

const openProducts = (row) => {
  currentSeller.value = row
  productSearch.value = ''
  products.value = []
  dialogVisible.value = true
  loadSellerProducts()
}

onMounted(loadSellers)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.page-header h1 { font-size: 22px; color: #303133; }
.pagination { display: flex; justify-content: center; margin-top: 20px; }
.product-cell { display: flex; align-items: center; gap: 10px; }
.thumb { width: 46px; height: 46px; border-radius: 4px; }
</style>
