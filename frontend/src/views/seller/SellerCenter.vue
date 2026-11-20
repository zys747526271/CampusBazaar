<template>
  <div class="seller-page">
    <div class="page-header">
      <div>
        <h1>卖家中心</h1>
        <p class="subtitle">管理你的商品、分类与订单</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>发布商品
      </el-button>
    </div>

    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="never"><div class="stat"><div class="num">{{ stats.product_count || 0 }}</div><div class="label">商品总数</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never"><div class="stat"><div class="num">{{ stats.on_sale_count || 0 }}</div><div class="label">在售商品</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never"><div class="stat"><div class="num">{{ stats.total_sold || 0 }}</div><div class="label">累计销量</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never"><div class="stat"><div class="num">{{ stats.total_views || 0 }}</div><div class="label">累计浏览</div></div></el-card>
      </el-col>
    </el-row>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="我的商品" name="products">
        <el-table :data="products" v-loading="loading" border style="width:100%">
          <el-table-column label="商品" min-width="200">
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
          <el-table-column label="销量 / 库存" width="130">
            <template #default="{ row }">{{ row.sold_count || 0 }} / {{ row.stock }}</template>
          </el-table-column>
          <el-table-column prop="views" label="浏览" width="80" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === '已通过' ? 'success' : row.status === '待审核' ? 'warning' : 'info'" size="small">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="280">
            <template #default="{ row }">
              <el-button size="small" text @click="openComments(row)">评论</el-button>
              <el-button size="small" type="primary" text @click="openEdit(row)">编辑</el-button>
              <el-button size="small" text @click="toggleProduct(row)">{{ row.is_available ? '下架' : '上架' }}</el-button>
              <el-button size="small" type="danger" text @click="removeProduct(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!products.length && !loading" description="还没有商品，点击右上角发布" />
      </el-tab-pane>

      <el-tab-pane label="我的分类" name="categories">
        <div class="category-toolbar">
          <el-input v-model="newCategory" placeholder="输入分类名称，如：考研资料" style="width:240px" @keyup.enter="addCategory" />
          <el-button type="primary" @click="addCategory">新增分类</el-button>
          <span class="hint">自己的分类只有自己可见，删除前需先转移该分类下的商品</span>
        </div>
        <el-table :data="categories" border style="width:100%;max-width:640px">
          <el-table-column prop="name" label="分类名称" />
          <el-table-column prop="sort_order" label="排序" width="90" />
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button size="small" text @click="renameCategory(row)">重命名</el-button>
              <el-button size="small" type="danger" text @click="deleteCategory(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!categories.length" description="还没有自定义分类" />
      </el-tab-pane>

      <el-tab-pane label="收到的订单" name="orders">
        <el-table :data="orders" border style="width:100%">
          <el-table-column prop="order_no" label="订单号" min-width="180" />
          <el-table-column prop="total_amount" label="金额" width="110">
            <template #default="{ row }">¥{{ Number(row.total_amount).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column label="我的商品">
            <template #default="{ row }">
              <span v-for="it in row.my_items" :key="it.product_id" class="order-item">
                ID {{ it.product_id }} × {{ it.quantity }}
              </span>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!orders.length" description="还没有收到订单" />
      </el-tab-pane>
    </el-tabs>

    <!-- 发布/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑商品' : '发布商品'" width="560px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="商品名称" />
        </el-form-item>
        <el-form-item label="价格" prop="price">
          <el-input-number v-model="form.price" :min="0" :precision="2" :step="1" />
        </el-form-item>
        <el-form-item label="库存" prop="quantity">
          <el-input-number v-model="form.quantity" :min="0" :step="1" />
        </el-form-item>
        <el-form-item label="我的分类">
          <el-select v-model="form.seller_category_id" placeholder="可不选" clearable style="width:100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="平台分类">
          <el-select v-model="form.tag_id" placeholder="选择分类" clearable style="width:100%">
            <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="商品图片">
          <el-upload
            :action="uploadUrl"
            :headers="uploadHeaders"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :show-file-list="false"
            accept="image/*"
          >
            <el-button size="small" type="primary">上传图片</el-button>
          </el-upload>
          <div class="image-preview">
            <div v-for="(img, index) in form.images" :key="index" class="image-item">
              <el-image :src="img" fit="cover" class="preview-thumb" />
              <el-button size="small" type="danger" text @click="form.images.splice(index, 1)">移除</el-button>
            </div>
          </div>
          <div class="hint">编辑时新增图片会立即保存；发布时图片随商品信息一起提交</div>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="商品成色、使用情况等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveProduct">保存</el-button>
      </template>
    </el-dialog>

    <!-- 商品评论对话框 -->
    <el-dialog v-model="commentsVisible" :title="`「${currentProductName}」的评论`" width="640px">
      <div v-if="comments.length">
        <div v-for="c in comments" :key="c.id" class="comment-item">
          <div class="comment-head">
            <strong>{{ c.user?.nickname || '匿名买家' }}</strong>
            <span class="rating">评分 {{ c.rating }}</span>
            <span class="time">{{ c.create_time }}</span>
            <el-tag v-if="c.is_hidden" type="info" size="small">已隐藏</el-tag>
          </div>
          <div class="comment-body">{{ c.content }}</div>
        </div>
      </div>
      <el-empty v-else description="该商品还没有评论" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/utils/api'

const activeTab = ref('products')
const products = ref([])
const orders = ref([])
const stats = ref({})
const tags = ref([])
const categories = ref([])
const comments = ref([])
const currentProductName = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const commentsVisible = ref(false)
const editing = ref(false)
const formRef = ref(null)
const newCategory = ref('')

const uploadUrl = '/api/products/upload-images'
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`
}))

const form = reactive({
  id: null, name: '', price: 0, quantity: 1,
  tag_id: null, seller_category_id: null, description: '', images: []
})
const rules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  description: [{ required: true, message: '请输入描述', trigger: 'blur' }]
}

const loadCategories = async () => {
  try {
    const resp = await api.seller.categories()
    categories.value = resp.data || []
  } catch (e) { categories.value = [] }
}

const loadAll = async () => {
  loading.value = true
  try {
    const [p, o, s, t] = await Promise.all([
      api.seller.myProducts(), api.seller.receivedOrders(),
      api.seller.stats(), api.tags.getList({ per_page: 100 })
    ])
    products.value = p.data || []
    orders.value = o.data || []
    stats.value = s.data || {}
    tags.value = t.data?.items || []
    stats.value.total_sold = products.value.reduce((sum, item) => sum + (item.sold_count || 0), 0)
  } catch (e) { /* 页面仍可展示已有数据 */ }
  finally { loading.value = false }
  await loadCategories()
}

const openCreate = () => {
  editing.value = false
  Object.assign(form, {
    id: null, name: '', price: 0, quantity: 1, tag_id: tags.value[0]?.id || null,
    seller_category_id: null, description: '', images: []
  })
  dialogVisible.value = true
}
const openEdit = (row) => {
  editing.value = true
  Object.assign(form, {
    id: row.id, name: row.name, price: row.price, quantity: row.quantity,
    tag_id: row.tag_id, seller_category_id: row.seller_category_id || null,
    description: row.description, images: [...(row.images || [])]
  })
  dialogVisible.value = true
}

const handleUploadSuccess = (resp) => {
  const url = resp?.data?.urls?.[0] || resp?.data?.url || resp?.data?.images?.[0]
  if (url && !form.images.includes(url)) form.images.push(url)
  ElMessage.success('图片已上传')
}
const handleUploadError = () => ElMessage.error('图片上传失败')

const saveProduct = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async valid => {
    if (!valid) return
    saving.value = true
    try {
      const payload = {
        name: form.name, price: form.price, quantity: form.quantity,
        tag_id: form.tag_id, seller_category_id: form.seller_category_id,
        description: form.description, images: form.images
      }
      const resp = editing.value
        ? await api.products.update(form.id, payload)
        : await api.products.create(payload)
      if (resp.success) {
        ElMessage.success(editing.value ? '已保存' : '发布成功')
        dialogVisible.value = false
        loadAll()
      } else {
        ElMessage.error(resp.message || '保存失败')
      }
    } catch (e) { ElMessage.error('保存失败') }
    finally { saving.value = false }
  })
}

const toggleProduct = async (row) => {
  try {
    const resp = await api.seller.toggleProduct(row.id)
    ElMessage.success(resp.message)
    loadAll()
  } catch (e) { ElMessage.error('操作失败') }
}

const removeProduct = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '提示', { type: 'warning' })
    const resp = await api.products.remove(row.id)
    if (resp.success) { ElMessage.success('已删除'); loadAll() }
  } catch (e) { if (e !== 'cancel') { /* ignore */ } }
}

const openComments = async (row) => {
  currentProductName.value = row.name
  try {
    const resp = await api.seller.productComments(row.id)
    comments.value = resp.data || []
    commentsVisible.value = true
  } catch (e) { ElMessage.error('获取评论失败') }
}

const addCategory = async () => {
  const name = newCategory.value.trim()
  if (!name) return ElMessage.warning('请输入分类名称')
  try {
    const resp = await api.seller.createCategory({ name })
    if (resp.success) { newCategory.value = ''; loadCategories(); ElMessage.success('分类已新增') }
    else ElMessage.error(resp.message)
  } catch (e) { ElMessage.error('新增失败') }
}

const renameCategory = async (row) => {
  try {
    const { value } = await ElMessageBox.prompt('输入新的分类名称', '重命名', {
      inputValue: row.name, inputValidator: v => !!v.trim() || '名称不能为空'
    })
    const resp = await api.seller.updateCategory(row.id, { name: value.trim() })
    if (resp.success) { loadCategories(); ElMessage.success('已重命名') }
    else ElMessage.error(resp.message)
  } catch (e) { if (e !== 'cancel') { /* ignore */ } }
}

const deleteCategory = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除分类「${row.name}」吗？`, '提示', { type: 'warning' })
    const resp = await api.seller.deleteCategory(row.id)
    if (resp.success) { loadCategories(); ElMessage.success('已删除') }
    else ElMessage.error(resp.message)
  } catch (e) { if (e !== 'cancel') { /* ignore */ } }
}

onMounted(loadAll)
</script>

<style scoped>
.seller-page { min-height: 60vh; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { font-size: 24px; color: #303133; }
.subtitle { color: #909399; font-size: 13px; margin-top: 4px; }
.stats-row { margin-bottom: 20px; }
.stat { text-align: center; padding: 10px 0; }
.stat .num { font-size: 28px; font-weight: 700; color: #409eff; }
.stat .label { color: #909399; font-size: 13px; margin-top: 4px; }
.product-cell { display: flex; align-items: center; gap: 10px; }
.thumb { width: 46px; height: 46px; border-radius: 4px; }
.order-item { display: inline-block; margin-right: 8px; color: #606266; font-size: 13px; }
.category-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.hint { color: #909399; font-size: 12px; }
.image-preview { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.image-item { display: flex; align-items: center; gap: 4px; }
.preview-thumb { width: 60px; height: 60px; border-radius: 4px; }
.comment-item { padding: 12px 0; border-bottom: 1px solid #ebeef5; }
.comment-head { display: flex; align-items: center; gap: 12px; font-size: 13px; }
.comment-head .rating { color: #e6a23c; }
.comment-head .time { color: #909399; margin-left: auto; }
.comment-body { margin-top: 8px; color: #606266; line-height: 1.6; }
</style>
