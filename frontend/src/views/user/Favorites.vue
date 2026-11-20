<template>
  <div class="list-page">
    <div class="page-header">
      <h1>我的收藏</h1>
      <el-button v-if="items.length" type="danger" plain @click="clearAll">清空收藏</el-button>
    </div>
    <div v-loading="loading">
      <el-row :gutter="20" v-if="items.length">
        <el-col :xs="12" :sm="8" :md="6" :lg="5" v-for="f in items" :key="f.id">
          <div class="fav-item">
            <product-card v-if="f.product" :product="f.product" />
            <el-button class="remove" size="small" type="danger" text @click="remove(f.product_id)">取消收藏</el-button>
          </div>
        </el-col>
      </el-row>
      <el-empty v-else-if="!loading" description="还没有收藏，去逛逛吧">
        <el-button type="primary" @click="$router.push('/products')">去逛逛</el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'
import ProductCard from '@/components/product/ProductCard.vue'

const items = ref([])
const loading = ref(false)

const load = async () => {
  loading.value = true
  try {
    const resp = await api.favorites.getList()
    items.value = resp.data || []
  } catch (e) { items.value = [] }
  finally { loading.value = false }
}

const remove = async (productId) => {
  try {
    await api.favorites.remove(productId)
    ElMessage.success('已取消收藏')
    load()
  } catch (e) { ElMessage.error('操作失败') }
}

const clearAll = async () => {
  try {
    await ElMessageBox.confirm('确定清空所有收藏吗？', '提示', { type: 'warning' })
    await Promise.all(items.value.map(f => api.favorites.remove(f.product_id)))
    ElMessage.success('已清空')
    load()
  } catch (e) { if (e !== 'cancel') { /* ignore */ } }
}

onMounted(load)
</script>

<style scoped>
.list-page { min-height: 60vh; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { font-size: 24px; color: #303133; }
.fav-item { position: relative; margin-bottom: 12px; }
.fav-item .remove { width: 100%; }
</style>
