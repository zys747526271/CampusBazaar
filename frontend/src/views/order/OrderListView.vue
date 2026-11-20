<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { orderApi } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppImage from '@/components/ui/AppImage.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import AppTabs from '@/components/ui/AppTabs.vue'
import StatusTag from '@/components/ui/StatusTag.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { ORDER_ACTION_TEXT, dateTime, money } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const orders = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const counts = ref({})
const busyId = ref(0)

const tabs = computed(() => [
  { label: '全部', value: '', badge: counts.value.total || 0 },
  { label: '待付款', value: '待付款', badge: counts.value['待付款'] || 0 },
  { label: '已付款', value: '已付款', badge: counts.value['已付款'] || 0 },
  { label: '已发货', value: '已发货', badge: counts.value['已发货'] || 0 },
  { label: '已完成', value: '已完成', badge: counts.value['已完成'] || 0 },
  { label: '退款中', value: '退款中', badge: counts.value['退款中'] || 0 },
  { label: '已取消', value: '已取消', badge: counts.value['已取消'] || 0 }
])
const activeTab = computed(() => route.query.status || '')

const loadCounts = async () => {
  try {
    const data = await orderApi.counts()
    counts.value = data.counts || {}
    counts.value.total = data.total || 0
  } catch (error) {
    counts.value = {}
  }
}

const load = async () => {
  loading.value = true
  try {
    const data = await orderApi.list({ status: activeTab.value || undefined, page: route.query.page || 1, per_page: 10 })
    orders.value = data.items || []
    total.value = data.total || 0
    pages.value = data.pages || 0
    page.value = data.page || 1
  } catch (error) {
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

const changeTab = (value) => {
  router.push({ path: '/orders', query: value ? { status: value } : {} })
}

const changePage = (next) => {
  router.push({ path: '/orders', query: { ...route.query, page: next } })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const runAction = async (order, action) => {
  if (action === 'comment') {
    router.push(`/orders/${order.id}`)
    return
  }
  if (action === 'confirm_offline') {
    toastSuccess('请等待卖家确认收款，确认后订单进入待发货')
    return
  }

  if (action === 'cancel') {
    const ok = await confirmAction({
      title: '取消订单',
      message: `确定取消订单 ${order.order_no} 吗？取消后库存会释放给其他同学。`,
      confirmText: '取消订单'
    })
    if (!ok) return
    busyId.value = order.id
    try {
      await orderApi.cancel(order.id, '买家主动取消')
      toastSuccess('订单已取消')
      load()
      loadCounts()
    } catch (error) {
      toastError(error.message)
    } finally {
      busyId.value = 0
    }
    return
  }

  if (action === 'pay') {
    const ok = await confirmAction({
      title: '余额支付',
      message: `将从余额扣除 ¥${money(order.total_amount)}，确认支付？`,
      confirmText: '确认支付',
      danger: false
    })
    if (!ok) return
    busyId.value = order.id
    try {
      await orderApi.pay(order.id)
      toastSuccess('支付成功')
      load()
      loadCounts()
    } catch (error) {
      toastError(error.message)
    } finally {
      busyId.value = 0
    }
    return
  }

  if (action === 'confirm') {
    const ok = await confirmAction({
      title: '确认收货',
      message: '请确认已收到商品并当面验货，确认后货款将结算给卖家。',
      confirmText: '确认收货',
      danger: false
    })
    if (!ok) return
    busyId.value = order.id
    try {
      await orderApi.confirm(order.id)
      toastSuccess('已确认收货，去给卖家一个评价吧')
      load()
      loadCounts()
    } catch (error) {
      toastError(error.message)
    } finally {
      busyId.value = 0
    }
    return
  }

  if (action === 'refund') {
    router.push(`/orders/${order.id}`)
  }
}

watch(() => route.query, () => {
  load()
  loadCounts()
})

onMounted(() => {
  load()
  loadCounts()
})
</script>

<template>
  <div class="orders">
    <div class="panel">
      <header class="head">
        <div>
          <h1>我的订单</h1>
          <p class="text-sm text-muted">共 {{ total }} 笔订单</p>
        </div>
        <RouterLink to="/products" class="btn btn-sm">继续逛逛</RouterLink>
      </header>
      <AppTabs :items="tabs" :model-value="activeTab" @change="changeTab" />
    </div>

    <div v-if="loading" class="loading">
      <SkeletonBlock v-for="i in 3" :key="i" :h="160" radius="12px" />
    </div>

    <AppEmpty
      v-else-if="!orders.length"
      icon="file-text"
      title="还没有订单"
      description="挑一件心仪的二手好物，开启第一次校园交易"
    >
      <RouterLink to="/products" class="btn btn-primary btn-sm">去逛逛</RouterLink>
    </AppEmpty>

    <div v-else class="order-list">
      <article v-for="order in orders" :key="order.id" class="order-card">
        <header class="order-head">
          <div class="head-left">
            <span class="order-no">{{ order.order_no }}</span>
            <span class="text-xs text-muted">{{ dateTime(order.created_at) }}</span>
            <RouterLink v-if="order.seller" :to="`/shops/${order.seller.id}`" class="text-xs seller">
              {{ order.seller.nickname }}
            </RouterLink>
          </div>
          <StatusTag :status="order.status" />
        </header>

        <RouterLink :to="`/orders/${order.id}`" class="order-body">
          <div v-for="item in order.items" :key="item.id" class="line">
            <AppImage :src="item.image" :alt="item.name" radius="9px" class="line-img" />
            <div class="line-info">
              <p class="line-name clamp-2">{{ item.name }}</p>
              <p class="text-xs text-muted">{{ item.condition }} · × {{ item.quantity }}</p>
            </div>
            <span class="price price-sm"><span class="unit">¥</span>{{ money(item.price) }}</span>
          </div>
        </RouterLink>

        <footer class="order-foot">
          <div class="amount">
            <span class="text-xs text-muted">{{ order.delivery_type }} · {{ order.pay_method }}</span>
            <span class="text-sm">合计</span>
            <span class="price price-md"><span class="unit">¥</span>{{ money(order.total_amount) }}</span>
          </div>
          <div class="ops">
            <button
              v-for="action in order.actions"
              :key="action"
              class="btn btn-sm"
              :class="{ 'btn-primary': ['pay', 'confirm'].includes(action) }"
              type="button"
              :disabled="busyId === order.id"
              @click="runAction(order, action)"
            >
              {{ ORDER_ACTION_TEXT[action] || action }}
            </button>
            <RouterLink :to="`/orders/${order.id}`" class="btn btn-sm">
              订单详情 <AppIcon name="chevron-right" :size="13" />
            </RouterLink>
          </div>
        </footer>
      </article>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="10" @change="changePage" />
    </div>
  </div>
</template>

<style scoped>
.orders { display: flex; flex-direction: column; gap: 14px; }
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.head h1 { font-size: 21px; letter-spacing: -.3px; }

.loading { display: flex; flex-direction: column; gap: 12px; }
.order-list { display: flex; flex-direction: column; gap: 12px; }

.order-card { background: #fff; border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.order-head {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 12px 18px; background: #fafbfc; border-bottom: 1px solid var(--line);
}
.head-left { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; min-width: 0; }
.order-no { font-family: var(--mono); font-size: 12.5px; color: var(--ink-2); }
.seller { color: var(--brand); }

.order-body { display: block; padding: 6px 18px; }
.line { display: flex; align-items: center; gap: 12px; padding: 10px 0; }
.line + .line { border-top: 1px dashed var(--line); }
.line-img { width: 72px; flex: none; }
.line-info { flex: 1; min-width: 0; }
.line-name { font-size: 13.5px; }

.order-foot {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 12px 18px; border-top: 1px solid var(--line); flex-wrap: wrap;
}
.amount { display: flex; align-items: baseline; gap: 8px; }
.ops { display: flex; gap: 8px; flex-wrap: wrap; }

@media (max-width: 720px) {
  .order-head { padding: 10px 12px; }
  .order-body { padding: 4px 12px; }
  .order-foot { padding: 10px 12px; }
  .ops { width: 100%; }
  .ops .btn { flex: 1; }
}
</style>
