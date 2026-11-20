<template>
  <div class="list-page">
    <div class="page-header">
      <h1>浏览记录</h1>
      <el-button v-if="items.length" type="danger" plain @click="clearAll">清空记录</el-button>
    </div>
    <div v-loading="loading">
      <el-row :gutter="20" v-if="items.length">
        <el-col :xs="12" :sm="8" :md="6" :lg="5" v-for="h in items" :key="h.id">
          <div class="history-item">
            <product-card v-if="h.product" :product="h.product" />
            <div class="time">浏览于 {{ formatTime(h.viewed_at) }}</div>
          </div>
        </el-col>
      </el-row>
      <el-empty v-else-if="!loading" description="还没有浏览记录">
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

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : ''
const load = async () => {
  loading.value = true
  try {
    const resp = await api.history.getList()
    items.value = resp.data || []
  } catch (e) { items.value = [] }
  finally { loading.value = false }
}
const clearAll = async () => {
  try {
    await ElMessageBox.confirm('确定清空浏览记录吗？', '提示', { type: 'warning' })
    await api.history.clear()
    ElMessage.success('已清空')
    load()
  } catch (e) { /* ignore */ }
}
onMounted(load)
</script>

<style scoped>
.list-page { min-height: 60vh; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { font-size: 24px; color: #303133; }
.history-item { margin-bottom: 12px; }
.history-item .time { font-size: 12px; color: #909399; text-align: center; margin-top: 4px; }
</style>
