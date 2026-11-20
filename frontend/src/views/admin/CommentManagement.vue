<template>
  <div class="comment-admin-page">
    <div class="page-header">
      <h1>评论管理</h1>
      <div class="filters">
        <el-input v-model="search" placeholder="搜索商品名或评论内容" style="width:240px" clearable @keyup.enter="loadComments" @clear="loadComments" />
        <el-select v-model="hiddenFilter" style="width:130px" @change="page = 1; loadComments()">
          <el-option label="全部状态" value="" />
          <el-option label="正常显示" value="false" />
          <el-option label="已隐藏" value="true" />
        </el-select>
        <el-button type="primary" @click="loadComments">搜索</el-button>
      </div>
    </div>

    <el-table :data="comments" v-loading="loading" border style="width:100%">
      <el-table-column prop="product_name" label="商品" min-width="160" />
      <el-table-column label="评论内容" min-width="260">
        <template #default="{ row }">
          <div>{{ row.content }}</div>
          <div class="meta">评分 {{ row.rating }} · {{ row.user?.nickname || '匿名' }} · {{ row.create_time }}</div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_hidden ? 'info' : 'success'" size="small">
            {{ row.is_hidden ? '已隐藏' : '正常' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" :type="row.is_hidden ? 'success' : 'warning'" text @click="toggleVisibility(row)">
            {{ row.is_hidden ? '恢复显示' : '隐藏评论' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!comments.length && !loading" description="暂无评论" />
    <div class="pagination" v-if="total > pageSize">
      <el-pagination background layout="prev, pager, next" :total="total" :page-size="pageSize"
        v-model:current-page="page" @current-change="loadComments" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const comments = ref([])
const search = ref('')
const hiddenFilter = ref('')
const loading = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)

const loadComments = async () => {
  loading.value = true
  try {
    const params = { page: page.value, per_page: pageSize, search: search.value }
    if (hiddenFilter.value) params.hidden = hiddenFilter.value
    const resp = await api.admin.getComments(params)
    comments.value = resp.data?.items || []
    total.value = resp.data?.total || 0
  } catch (e) { ElMessage.error('获取评论失败') }
  finally { loading.value = false }
}

const toggleVisibility = async (row) => {
  try {
    const resp = await api.admin.toggleCommentVisibility(row.id, { is_hidden: !row.is_hidden })
    if (resp.success) { ElMessage.success(resp.message); loadComments() }
    else ElMessage.error(resp.message)
  } catch (e) { ElMessage.error('操作失败') }
}

onMounted(loadComments)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; flex-wrap: wrap; gap: 12px; }
.page-header h1 { font-size: 22px; color: #303133; }
.filters { display: flex; gap: 10px; }
.meta { color: #909399; font-size: 12px; margin-top: 4px; }
.pagination { display: flex; justify-content: center; margin-top: 20px; }
</style>
