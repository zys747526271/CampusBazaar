<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { cartApi } from '@/api'
import { useCartStore } from '@/stores/cart'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppImage from '@/components/ui/AppImage.vue'
import AppStepper from '@/components/ui/AppStepper.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { money } from '@/utils/format'

const router = useRouter()
const cartStore = useCartStore()

const loading = ref(true)
const items = ref([])
const summary = ref({ total_count: 0, valid_count: 0, invalid_count: 0, selected_count: 0, selected_amount: 0 })
const busyId = ref(0)
const allSelected = ref(false)

const validItems = computed(() => items.value.filter((item) => !item.invalid_reason))
const invalidItems = computed(() => items.value.filter((item) => item.invalid_reason))
const canCheckout = computed(() => summary.value.selected_count > 0)

const load = async () => {
  loading.value = true
  try {
    const data = await cartApi.list()
    items.value = data.items || []
    summary.value = data.summary
    allSelected.value = validItems.value.length > 0 && validItems.value.every((item) => item.selected)
    cartStore.setCount(summary.value.total_count)
  } catch (error) {
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

const applyResult = (data) => {
  if (data?.summary) {
    summary.value = data.summary
    cartStore.setCount(data.summary.total_count)
  }
}

const toggleSelect = async (item) => {
  busyId.value = item.id
  try {
    const data = await cartApi.update(item.id, { selected: !item.selected })
    item.selected = !item.selected
    applyResult(data)
    allSelected.value = validItems.value.length > 0 && validItems.value.every((row) => row.selected)
  } catch (error) {
    toastError(error.message)
  } finally {
    busyId.value = 0
  }
}

const changeQuantity = async (item, value) => {
  busyId.value = item.id
  try {
    const data = await cartApi.update(item.id, { quantity: value })
    item.quantity = value
    item.subtotal = value * Number(item.product.price)
    applyResult(data)
  } catch (error) {
    toastError(error.message)
    load()
  } finally {
    busyId.value = 0
  }
}

const removeItem = async (item) => {
  const ok = await confirmAction({
    title: '移除商品',
    message: `确定把《${item.product.name}》从购物车移除吗？`,
    confirmText: '移除'
  })
  if (!ok) return
  try {
    await cartApi.remove(item.id)
    toastSuccess('已移除')
    load()
  } catch (error) {
    toastError(error.message)
  }
}

const toggleAll = async () => {
  const next = !allSelected.value
  try {
    await cartApi.selectAll(next)
    items.value.forEach((item) => {
      if (!item.invalid_reason) item.selected = next
    })
    allSelected.value = next
    const data = await cartApi.list()
    summary.value = data.summary
  } catch (error) {
    toastError(error.message)
  }
}

const clearInvalid = async () => {
  const ok = await confirmAction({
    title: '清理失效商品',
    message: `将移除 ${invalidItems.value.length} 件已下架或售罄的商品。`,
    confirmText: '清理'
  })
  if (!ok) return
  try {
    await cartApi.clear('invalid')
    toastSuccess('已清理')
    load()
  } catch (error) {
    toastError(error.message)
  }
}

const checkout = () => {
  if (!canCheckout.value) {
    toastError('请先勾选要结算的商品')
    return
  }
  router.push('/checkout')
}

onMounted(load)
</script>

<template>
  <div class="container cart-page">
    <header class="page-head">
      <h1>购物车</h1>
      <p class="text-sm text-muted">共 {{ summary.total_count }} 件商品，已选中 {{ summary.selected_count }} 件</p>
    </header>

    <div v-if="loading" class="panel loading">
      <SkeletonBlock v-for="i in 3" :key="i" :h="96" radius="10px" />
    </div>

    <AppEmpty
      v-else-if="!items.length"
      icon="cart"
      title="购物车还是空的"
      description="把心仪的二手好物加进来，一起结算更方便"
    >
      <RouterLink to="/products" class="btn btn-primary">去逛逛</RouterLink>
    </AppEmpty>

    <template v-else>
      <div class="panel cart-panel">
        <div class="cart-head">
          <label class="check">
            <input type="checkbox" :checked="allSelected" @change="toggleAll" />
            <span>全选</span>
          </label>
          <span class="col-price">单价</span>
          <span class="col-qty">数量</span>
          <span class="col-sub">小计</span>
          <span class="col-op">操作</span>
        </div>
        <ul class="cart-list">
          <li v-for="item in validItems" :key="item.id" class="cart-item">
            <label class="check">
              <input type="checkbox" :checked="item.selected" @change="toggleSelect(item)" />
            </label>
            <RouterLink :to="`/products/${item.product.id}`" class="thumb">
              <AppImage :src="item.product.cover_image" :alt="item.product.name" radius="9px" />
            </RouterLink>
            <div class="info">
              <RouterLink :to="`/products/${item.product.id}`" class="name clamp-2">{{ item.product.name }}</RouterLink>
              <div class="tags">
                <span class="tag tag-line">{{ item.product.condition }}</span>
                <span class="text-xs text-muted">库存 {{ item.product.quantity }}</span>
                <RouterLink :to="`/shops/${item.product.seller.id}`" class="text-xs seller-link">
                  {{ item.product.seller.nickname }}
                </RouterLink>
              </div>
            </div>
            <div class="col-price price price-sm"><span class="unit">¥</span>{{ money(item.product.price) }}</div>
            <div class="col-qty">
              <AppStepper
                :model-value="item.quantity"
                :max="item.product.quantity"
                size="sm"
                :disabled="busyId === item.id"
                @change="changeQuantity(item, $event)"
              />
            </div>
            <div class="col-sub price price-sm"><span class="unit">¥</span>{{ money(item.subtotal) }}</div>
            <div class="col-op">
              <button class="btn-text" type="button" @click="removeItem(item)">移除</button>
            </div>
          </li>
        </ul>

        <div v-if="invalidItems.length" class="invalid-block">
          <div class="invalid-head">
            <span><AppIcon name="alert" :size="14" /> 失效商品 {{ invalidItems.length }} 件</span>
            <button class="btn-text" type="button" @click="clearInvalid">清空失效商品</button>
          </div>
          <ul>
            <li v-for="item in invalidItems" :key="item.id" class="invalid-item">
              <span class="tag">{{ item.invalid_reason }}</span>
              <span class="ellipsis invalid-name">{{ item.product?.name || '商品已删除' }}</span>
              <button class="btn-text" type="button" @click="removeItem(item)">移除</button>
            </li>
          </ul>
        </div>
      </div>

      <div class="summary-bar">
        <label class="check">
          <input type="checkbox" :checked="allSelected" @change="toggleAll" />
          <span>全选</span>
        </label>
        <span class="text-sm text-muted">已选 {{ summary.selected_count }} 件</span>
        <div class="total">
          <span class="text-sm">合计：</span>
          <span class="price price-md"><span class="unit">¥</span>{{ money(summary.selected_amount) }}</span>
        </div>
        <button class="btn btn-primary btn-lg" type="button" :disabled="!canCheckout" @click="checkout">
          去结算
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.cart-page { padding-top: 22px; }
.page-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 16px; }
.page-head h1 { font-size: 24px; letter-spacing: -.4px; }

.loading { display: flex; flex-direction: column; gap: 12px; }
.cart-panel { padding: 0 22px 8px; }

.cart-head {
  display: grid; grid-template-columns: 32px 88px minmax(0, 1fr) 110px 132px 110px 64px;
  align-items: center; gap: 12px;
  padding: 14px 0; border-bottom: 1px solid var(--line);
  color: var(--muted); font-size: 12px;
}
.cart-head .check { grid-column: span 3; display: flex; align-items: center; gap: 8px; }

.cart-list { display: flex; flex-direction: column; }
.cart-item {
  display: grid; grid-template-columns: 32px 88px minmax(0, 1fr) 110px 132px 110px 64px;
  align-items: center; gap: 12px;
  padding: 18px 0; border-bottom: 1px solid var(--line);
}
.cart-item:last-child { border-bottom: none; }

.check { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: var(--ink-2); }
.check input { width: 16px; height: 16px; accent-color: var(--brand); cursor: pointer; }

.thumb { width: 88px; }
.info { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.name { font-size: 14px; font-weight: 500; }
.name:hover { color: var(--brand); }
.tags { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.seller-link:hover { color: var(--brand); }
.col-sub { font-weight: 700; }

.invalid-block { border-top: 1px dashed var(--line); padding: 14px 0 6px; }
.invalid-head {
  display: flex; align-items: center; justify-content: space-between;
  color: var(--muted); font-size: 12.5px;
}
.invalid-head span { display: inline-flex; align-items: center; gap: 5px; }
.invalid-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 0;
  color: var(--muted); font-size: 13px;
}
.invalid-name { flex: 1; min-width: 0; }

.summary-bar {
  position: sticky; bottom: 16px; z-index: 20;
  display: flex; align-items: center; gap: 18px;
  margin-top: 16px; padding: 12px 18px;
  background: rgba(255, 255, 255, .96); backdrop-filter: blur(10px);
  border: 1px solid var(--line); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}
.total { margin-left: auto; display: flex; align-items: baseline; gap: 4px; }
.summary-bar .btn { min-width: 148px; }

@media (max-width: 900px) {
  .cart-head { display: none; }
  .cart-item {
    grid-template-columns: 24px 76px minmax(0, 1fr);
    grid-template-areas:
      'check thumb info'
      '. qty price';
    row-gap: 10px;
  }
  .cart-item .check { grid-area: check; }
  .cart-item .thumb { grid-area: thumb; width: 76px; }
  .cart-item .info { grid-area: info; }
  .cart-item .col-price { display: none; }
  .cart-item .col-qty { grid-area: qty; }
  .cart-item .col-sub { grid-area: price; justify-self: end; }
  .cart-item .col-op { grid-column: 3; justify-self: end; }
  .summary-bar { gap: 10px; padding: 10px 12px; flex-wrap: wrap; }
  .summary-bar .btn { width: 100%; }
  .total { margin-left: auto; }
}
</style>
