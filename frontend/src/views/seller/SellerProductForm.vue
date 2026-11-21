<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { sellerApi, uploadApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { toastError, toastSuccess } from '@/composables/useToast'
import PageHeader from '@/components/ui/PageHeader.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppImage from '@/components/ui/AppImage.vue'
import AppModal from '@/components/ui/AppModal.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusTag from '@/components/ui/StatusTag.vue'
import { CONDITION_LIST, money, pickFieldErrors } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const app = useAppStore()

const isEdit = computed(() => Boolean(route.params.id))
const loading = ref(Boolean(route.params.id))
const saving = ref(false)
const uploading = ref(false)
const errors = reactive({})
const categories = ref([])
const current = ref(null)

const form = reactive({
  name: '',
  description: '',
  price: '',
  original_price: '',
  quantity: 1,
  condition: '几乎全新',
  location: '',
  tag_id: '',
  seller_category_id: '',
  images: [],
  supports_pickup: true,
  pickup_location: '',
  supports_express: true,
  free_shipping: true,
  shipping_fee: ''
})

const maxImages = computed(() => app.options?.max_images || 5)

const categoryOpen = ref(false)
const categoryName = ref('')
const categoryBusy = ref(false)

const loadCategories = async () => {
  try {
    const data = await sellerApi.categories()
    categories.value = data.items || []
  } catch (error) {
    categories.value = []
  }
}

const loadProduct = async () => {
  if (!isEdit.value) return
  try {
    const data = await sellerApi.product(route.params.id)
    current.value = data
    Object.assign(form, {
      name: data.name,
      description: data.description || '',
      price: String(data.price),
      original_price: data.original_price ? String(data.original_price) : '',
      quantity: data.quantity,
      condition: data.condition,
      location: data.location || '',
      tag_id: data.tag_id || '',
      seller_category_id: data.seller_category_id || '',
      images: [...(data.images || [])],
      supports_pickup: data.supports_pickup !== false,
      pickup_location: data.pickup_location || '',
      supports_express: data.supports_express !== false,
      free_shipping: data.free_shipping !== false,
      shipping_fee: data.shipping_fee ? String(data.shipping_fee) : ''
    })
  } catch (error) {
    toastError(error.message)
    router.replace('/seller/products')
  } finally {
    loading.value = false
  }
}

const pickImages = async (event) => {
  const files = Array.from(event.target.files || [])
  if (!files.length) return
  if (form.images.length + files.length > maxImages.value) {
    toastError(`最多上传 ${maxImages.value} 张图片`)
    event.target.value = ''
    return
  }
  uploading.value = true
  try {
    for (const file of files) {
      if (file.size > 5 * 1024 * 1024) {
        toastError(`${file.name} 超过 5MB，已跳过`)
        continue
      }
      const data = await uploadApi.image(file)
      form.images.push(data.url)
    }
    toastSuccess('图片上传成功')
  } catch (error) {
    toastError(error.message)
  } finally {
    uploading.value = false
    event.target.value = ''
  }
}

const removeImage = (index) => {
  form.images.splice(index, 1)
}

const makeCover = (index) => {
  const [image] = form.images.splice(index, 1)
  form.images.unshift(image)
}

const createCategory = async () => {
  if (!categoryName.value.trim()) {
    toastError('请输入分类名称')
    return
  }
  categoryBusy.value = true
  try {
    const created = await sellerApi.createCategory({ name: categoryName.value.trim() })
    categories.value.push(created)
    form.seller_category_id = created.id
    categoryOpen.value = false
    categoryName.value = ''
    toastSuccess('分类已创建')
  } catch (error) {
    toastError(error.message)
  } finally {
    categoryBusy.value = false
  }
}

const validate = () => {
  Object.keys(errors).forEach((key) => delete errors[key])
  if (form.name.trim().length < 2) errors.name = '商品名称至少 2 个字'
  if (!form.images.length) errors.images = '请至少上传一张商品图片'
  if (!form.tag_id) errors.tag_id = '请选择平台分类'
  const price = Number(form.price)
  if (!price || price <= 0) errors.price = '请输入正确的价格'
  if (form.original_price && Number(form.original_price) < price) errors.original_price = '原价不能低于售价'
  if (!Number(form.quantity) || Number(form.quantity) < 1) errors.quantity = '库存至少为 1'
  if (!form.supports_pickup && !form.supports_express) errors.delivery = '自提与快递至少选择一种'
  if (form.supports_express && !form.free_shipping && !(Number(form.shipping_fee) > 0)) {
    errors.shipping_fee = '不包邮时请填写运费'
  }
  return Object.keys(errors).length === 0
}

const submit = async () => {
  if (!validate()) return
  saving.value = true
  const payload = {
    name: form.name.trim(),
    description: form.description.trim(),
    price: Number(form.price).toFixed(2),
    original_price: form.original_price ? Number(form.original_price).toFixed(2) : '',
    quantity: Number(form.quantity),
    condition: form.condition,
    location: form.location.trim(),
    tag_id: Number(form.tag_id),
    seller_category_id: form.seller_category_id ? Number(form.seller_category_id) : 0,
    images: form.images,
    supports_pickup: form.supports_pickup,
    pickup_location: form.pickup_location.trim(),
    supports_express: form.supports_express,
    free_shipping: form.free_shipping,
    shipping_fee: form.supports_express && !form.free_shipping ? Number(form.shipping_fee).toFixed(2) : '0.00'
  }
  try {
    if (isEdit.value) {
      await sellerApi.updateProduct(route.params.id, payload)
      toastSuccess('商品已更新')
      router.push('/seller/products')
    } else {
      const created = await sellerApi.createProduct(payload)
      toastSuccess(created.status === '待审核' ? '已提交审核，通过后自动上架' : '发布成功')
      router.push('/seller/products')
    }
  } catch (error) {
    Object.assign(errors, pickFieldErrors(error))
    toastError(error.message)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([app.loadFilters(), loadCategories()])
  if (form.tag_id === '' && app.tags.length) form.tag_id = app.tags[0].id
  await loadProduct()
})
</script>

<template>
  <div class="product-form">
    <PageHeader
      :title="isEdit ? '编辑商品' : '发布商品'"
      :subtitle="isEdit ? '修改后立即生效，请确保描述与成色一致' : '真实描述 + 实拍图片，更容易卖出去'"
    >
      <template #actions>
        <RouterLink to="/seller/products" class="btn btn-sm">返回商品列表</RouterLink>
      </template>
    </PageHeader>

    <div v-if="loading" class="panel loading">
      <SkeletonBlock :h="40" radius="8px" />
      <SkeletonBlock :h="200" radius="8px" />
    </div>

    <div v-else class="layout">
      <div class="main">
        <section class="panel">
          <h2 class="block-title">基本信息</h2>

          <div v-if="current" class="status-line">
            <StatusTag :status="current.status" kind="product" />
            <span v-if="current.reject_reason" class="text-sm text-danger">驳回原因：{{ current.reject_reason }}</span>
            <span v-else class="text-sm text-muted">当前库存 {{ current.quantity }} 件 · 已售 {{ current.sales }}</span>
          </div>

          <div class="field mt-16">
            <label>商品名称 <em>*</em></label>
            <input v-model="form.name" class="input" :class="{ 'has-error': errors.name }" maxlength="80" placeholder="例如：高等数学 同济第七版 上下册" />
            <span class="field-hint">{{ form.name.length }}/80</span>
            <span v-if="errors.name" class="field-error">{{ errors.name }}</span>
          </div>

          <div class="grid-2 mt-12">
            <div class="field">
              <label>平台分类 <em>*</em></label>
              <select v-model="form.tag_id" class="select" :class="{ 'has-error': errors.tag_id }">
                <option value="" disabled>请选择分类</option>
                <option v-for="tag in app.tags" :key="tag.id" :value="tag.id">{{ tag.name }}</option>
              </select>
              <span v-if="errors.tag_id" class="field-error">{{ errors.tag_id }}</span>
            </div>
            <div class="field">
              <label>自定义分类（选填）</label>
              <div class="row gap-8">
                <select v-model="form.seller_category_id" class="select">
                  <option value="">不归类</option>
                  <option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option>
                </select>
                <button class="btn" type="button" @click="categoryOpen = true">新建</button>
              </div>
            </div>
          </div>

          <div class="grid-3 mt-12">
            <div class="field">
              <label>售价（元） <em>*</em></label>
              <input v-model="form.price" class="input" :class="{ 'has-error': errors.price }" inputmode="decimal" placeholder="0.00" />
              <span v-if="errors.price" class="field-error">{{ errors.price }}</span>
            </div>
            <div class="field">
              <label>原价（选填）</label>
              <input v-model="form.original_price" class="input" :class="{ 'has-error': errors.original_price }" inputmode="decimal" placeholder="划线价" />
              <span v-if="errors.original_price" class="field-error">{{ errors.original_price }}</span>
            </div>
            <div class="field">
              <label>库存 <em>*</em></label>
              <input v-model="form.quantity" class="input" :class="{ 'has-error': errors.quantity }" inputmode="numeric" placeholder="1" />
              <span v-if="errors.quantity" class="field-error">{{ errors.quantity }}</span>
            </div>
          </div>

          <div class="grid-2 mt-12">
            <div class="field">
              <label>成色</label>
              <select v-model="form.condition" class="select">
                <option v-for="item in CONDITION_LIST" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="field">
              <label>交易地点（选填）</label>
              <input v-model="form.location" class="input" maxlength="60" placeholder="例如：图书馆一楼大厅" />
            </div>
          </div>

          <div class="field mt-12">
            <label>商品描述</label>
            <textarea
              v-model="form.description"
              class="textarea"
              maxlength="2000"
              placeholder="写清使用时长、成色细节、配件是否齐全，减少沟通成本"
            />
            <span class="field-hint">{{ form.description.length }}/2000</span>
          </div>
        </section>

        <section class="panel">
          <h2 class="block-title">履约方式</h2>
          <p class="field-hint">自提即当面交易；快递需要填写运费或选择包邮。</p>

          <label class="check mt-12">
            <input v-model="form.supports_pickup" type="checkbox" /> 支持买家自提
          </label>
          <div v-if="form.supports_pickup" class="field mt-8">
            <label>自提点（可留空）</label>
            <input v-model="form.pickup_location" class="input" maxlength="120" placeholder="例如：图书馆一楼大厅 / 3 号宿舍楼下" />
            <span class="field-hint">留空时，买家下单后由你补充自提点，系统会自动通知买家</span>
          </div>

          <label class="check mt-16">
            <input v-model="form.supports_express" type="checkbox" /> 支持快递发货
          </label>
          <div v-if="form.supports_express" class="grid-2 mt-8">
            <div class="field">
              <label>邮费</label>
              <label class="check"><input v-model="form.free_shipping" type="checkbox" /> 包邮</label>
            </div>
            <div v-if="!form.free_shipping" class="field">
              <label>运费金额（元）</label>
              <input v-model="form.shipping_fee" class="input" :class="{ 'has-error': errors.shipping_fee }" inputmode="decimal" placeholder="例如：12.00" />
              <span v-if="errors.shipping_fee" class="field-error">{{ errors.shipping_fee }}</span>
            </div>
          </div>
          <span v-if="errors.delivery" class="field-error">{{ errors.delivery }}</span>
        </section>

        <section class="panel">
          <div class="block-head">
            <h2 class="block-title">商品图片 <em>*</em></h2>
            <span class="text-sm text-muted">{{ form.images.length }}/{{ maxImages }} 张 · 第一张为封面</span>
          </div>
          <div class="images">
            <div v-for="(image, index) in form.images" :key="image" class="image-item">
              <AppImage :src="image" :alt="`商品图 ${index + 1}`" radius="9px" />
              <span v-if="index === 0" class="cover-tag">封面</span>
              <div class="image-ops">
                <button v-if="index !== 0" type="button" @click="makeCover(index)">设为封面</button>
                <button type="button" class="danger" @click="removeImage(index)">删除</button>
              </div>
            </div>
            <label v-if="form.images.length < maxImages" class="uploader" :class="{ disabled: uploading }">
              <AppIcon :name="uploading ? 'refresh' : 'camera'" :size="22" />
              <span>{{ uploading ? '上传中…' : '添加图片' }}</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" multiple hidden :disabled="uploading" @change="pickImages" />
            </label>
          </div>
          <span v-if="errors.images" class="field-error">{{ errors.images }}</span>
          <p class="field-hint mt-8">支持 JPG / PNG / WebP，单张不超过 5MB，最多 {{ maxImages }} 张</p>
        </section>

        <div class="submit-bar">
          <RouterLink to="/seller/products" class="btn">取消</RouterLink>
          <button class="btn btn-primary btn-lg" type="button" :disabled="saving" @click="submit">
            {{ saving ? '提交中…' : isEdit ? '保存修改' : '发布商品' }}
          </button>
        </div>
      </div>

      <aside class="side">
        <div class="panel preview">
          <h3>买家看到的样子</h3>
          <AppImage :src="form.images[0]" :alt="form.name" radius="10px" />
          <p class="pv-name clamp-2">{{ form.name || '商品名称' }}</p>
          <div class="pv-price">
            <span class="price price-md"><span class="unit">¥</span>{{ money(form.price || 0) }}</span>
            <span v-if="form.original_price" class="origin">¥{{ money(form.original_price) }}</span>
          </div>
          <span class="tag tag-line">{{ form.condition }}</span>
          <div class="pv-delivery">
            <span v-if="form.supports_pickup" class="tag tag-line">自提</span>
            <span v-if="form.supports_express" class="tag tag-line">{{ form.free_shipping ? '包邮' : `运费 ¥${money(form.shipping_fee || 0)}` }}</span>
          </div>
        </div>

        <div class="panel tips">
          <h3><AppIcon name="info" :size="15" /> 发布建议</h3>
          <ul>
            <li>真实实拍图，避免使用官方宣传图</li>
            <li>标题写清品牌、型号、成色关键词</li>
            <li>价格参考同款二手成交价，更容易出手</li>
            <li>写清瑕疵与配件，能显著减少纠纷</li>
          </ul>
        </div>
      </aside>
    </div>

    <AppModal v-model="categoryOpen" title="新建自定义分类" width="400px">
      <div class="field">
        <label>分类名称</label>
        <input v-model="categoryName" class="input" maxlength="30" placeholder="例如：考研资料、宿舍小家电" />
      </div>
      <template #footer>
        <button class="btn" type="button" @click="categoryOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="categoryBusy" @click="createCategory">创建</button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.check { display: inline-flex; align-items: center; gap: 8px; font-size: 13.5px; color: var(--ink-2); }
.check input { accent-color: var(--brand); }
.pv-delivery { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
.loading { display: flex; flex-direction: column; gap: 14px; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 14px; align-items: start; }
.main { display: flex; flex-direction: column; gap: 14px; min-width: 0; }

.block-title { font-size: 15.5px; }
.block-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 12px; }
.status-line { display: flex; align-items: center; gap: 10px; background: #fafbfc; border-radius: 8px; padding: 8px 12px; }

.grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
em { color: var(--danger); font-style: normal; }
.field-hint { font-size: 11.5px; color: var(--muted); }

.images { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.image-item { position: relative; }
.image-item :deep(.app-image) { border: 1px solid var(--line); }
.cover-tag {
  position: absolute; left: 6px; top: 6px;
  background: var(--brand); color: #fff; font-size: 10.5px;
  padding: 1px 7px; border-radius: 5px;
}
.image-ops {
  position: absolute; inset: auto 0 0 0; display: flex; gap: 4px; padding: 5px;
  background: linear-gradient(transparent, rgba(15, 20, 28, .58)); border-radius: 0 0 9px 9px;
  opacity: 0; transition: opacity .16s;
}
.image-item:hover .image-ops { opacity: 1; }
.image-ops button {
  flex: 1; border: none; background: rgba(255, 255, 255, .92);
  border-radius: 5px; font-size: 10.5px; padding: 3px 0; color: var(--ink-2);
}
.image-ops button.danger { color: var(--danger); }

.uploader {
  aspect-ratio: 1 / 1; border: 1px dashed var(--line-strong); border-radius: 9px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  color: var(--muted); font-size: 12px; cursor: pointer; background: #fafbfc;
  transition: all .16s;
}
.uploader:hover { border-color: var(--brand); color: var(--brand); background: var(--brand-soft); }
.uploader.disabled { opacity: .6; pointer-events: none; }

.submit-bar { display: flex; justify-content: flex-end; gap: 10px; padding: 8px 0 12px; }

.side { display: flex; flex-direction: column; gap: 14px; position: sticky; top: 120px; }
.preview h3 { font-size: 13px; color: var(--muted); margin-bottom: 10px; }
.pv-name { margin-top: 10px; font-size: 13.5px; }
.pv-price { display: flex; align-items: baseline; gap: 8px; margin: 6px 0 8px; }
.origin { color: var(--muted-2); font-size: 12px; text-decoration: line-through; }

.tips h3 { display: flex; align-items: center; gap: 6px; font-size: 13px; margin-bottom: 10px; }
.tips li { font-size: 12.5px; color: var(--muted); line-height: 1.8; padding-left: 12px; position: relative; }
.tips li::before { content: ''; position: absolute; left: 2px; top: 9px; width: 4px; height: 4px; border-radius: 50%; background: #d3d8e0; }

@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  .side { position: static; }
  .images { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .grid-3 { grid-template-columns: 1fr; }
}
</style>
