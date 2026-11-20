<script setup>
import { computed, onMounted, ref } from 'vue'
import { sellerApi } from '@/api'
import { toastError } from '@/composables/useToast'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatCard from '@/components/ui/StatCard.vue'
import StatusTag from '@/components/ui/StatusTag.vue'
import AppImage from '@/components/ui/AppImage.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { dateTime, money } from '@/utils/format'

const loading = ref(true)
const data = ref({
  today_sales: 0,
  total_sales: 0,
  today_orders: 0,
  total_orders: 0,
  pending_ship: 0,
  refunding: 0,
  unpaid: 0,
  product_count: 0,
  on_sale_count: 0,
  pending_audit: 0,
  total_views: 0,
  recent_orders: [],
  top_products: []
})

const cards = computed(() => [
  { label: '今日销售额', value: `¥${money(data.value.today_sales)}`, hint: `今日 ${data.value.today_orders} 笔订单`, icon: 'trend-up', tone: 'brand' },
  { label: '累计销售额', value: `¥${money(data.value.total_sales)}`, hint: `共 ${data.value.total_orders} 笔订单`, icon: 'wallet', tone: 'ok' },
  { label: '待发货', value: data.value.pending_ship, hint: '买家已付款，尽快安排', icon: 'truck', tone: 'warn' },
  { label: '在售商品', value: data.value.on_sale_count, hint: `全部 ${data.value.product_count} 件 · 待审核 ${data.value.pending_audit}`, icon: 'package', tone: 'info' }
])

const load = async () => {
  loading.value = true
  try {
    data.value = await sellerApi.overview()
  } catch (error) {
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="dashboard">
    <PageHeader title="经营概览" subtitle="今天的生意怎么样？待发货与退款要及时处理">
      <template #actions>
        <RouterLink to="/seller/products/new" class="btn btn-primary btn-sm">
          <AppIcon name="plus" :size="14" /> 发布商品
        </RouterLink>
        <RouterLink to="/seller/orders" class="btn btn-sm">处理订单</RouterLink>
      </template>
    </PageHeader>

    <div class="stats">
      <StatCard v-for="card in cards" :key="card.label" v-bind="card" />
    </div>

    <div v-if="data.refunding || data.unpaid" class="alerts">
      <RouterLink v-if="data.pending_ship" to="/seller/orders?status=已付款" class="alert alert-warn">
        <AppIcon name="truck" :size="15" />
        有 {{ data.pending_ship }} 笔订单等待发货
        <AppIcon name="chevron-right" :size="13" class="ml" />
      </RouterLink>
      <RouterLink v-if="data.refunding" to="/seller/orders?status=退款中" class="alert alert-danger">
        <AppIcon name="alert" :size="15" />
        有 {{ data.refunding }} 笔退款申请待处理
        <AppIcon name="chevron-right" :size="13" class="ml" />
      </RouterLink>
      <RouterLink v-if="data.unpaid" to="/seller/orders?status=待付款" class="alert">
        <AppIcon name="clock" :size="15" />
        有 {{ data.unpaid }} 笔订单待买家付款
      </RouterLink>
    </div>

    <div class="grid">
      <section class="panel">
        <div class="card-head">
          <h2>最近订单</h2>
          <RouterLink to="/seller/orders" class="text-sm link">查看全部</RouterLink>
        </div>
        <div v-if="loading" class="loading">
          <SkeletonBlock v-for="i in 4" :key="i" :h="44" radius="8px" />
        </div>
        <AppEmpty v-else-if="!data.recent_orders.length" icon="truck" title="还没有订单" description="发布商品后，订单会出现在这里" compact />
        <table v-else class="table">
          <thead>
            <tr><th>订单号</th><th>商品</th><th>金额</th><th>状态</th><th>时间</th></tr>
          </thead>
          <tbody>
            <tr v-for="order in data.recent_orders" :key="order.id">
              <td class="mono">{{ order.order_no }}</td>
              <td class="ellipsis cell-name">{{ order.items?.[0]?.name || '—' }}</td>
              <td class="price price-sm"><span class="unit">¥</span>{{ money(order.total_amount) }}</td>
              <td><StatusTag :status="order.status" /></td>
              <td class="text-muted nowrap">{{ dateTime(order.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="panel">
        <div class="card-head">
          <h2>热销商品</h2>
          <RouterLink to="/seller/products" class="text-sm link">管理商品</RouterLink>
        </div>
        <div v-if="loading" class="loading">
          <SkeletonBlock v-for="i in 4" :key="i" :h="44" radius="8px" />
        </div>
        <AppEmpty v-else-if="!data.top_products.length" icon="package" title="还没有商品" description="去发布第一件闲置吧" compact />
        <ul v-else class="top-list">
          <li v-for="product in data.top_products" :key="product.id" class="top-item">
            <AppImage :src="product.cover_image" :alt="product.name" radius="8px" class="top-img" />
            <div class="top-info">
              <RouterLink :to="`/products/${product.id}`" class="ellipsis top-name">{{ product.name }}</RouterLink>
              <span class="text-xs text-muted">已售 {{ product.sales }} · 浏览 {{ product.views }}</span>
            </div>
            <span class="price price-sm"><span class="unit">¥</span>{{ money(product.price) }}</span>
          </li>
        </ul>
      </section>
    </div>

    <section class="panel mini-stats">
      <div><span>总浏览量</span><strong>{{ data.total_views }}</strong></div>
      <div><span>待审核</span><strong>{{ data.pending_audit }}</strong></div>
      <div><span>退款处理中</span><strong>{{ data.refunding }}</strong></div>
      <div><span>累计成交单</span><strong>{{ data.total_orders }}</strong></div>
    </section>
  </div>
</template>

<style scoped>
.stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.alerts { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.alerts .alert { align-items: center; }
.alerts .ml { margin-left: auto; }

.grid { display: grid; grid-template-columns: 1.35fr 1fr; gap: 14px; margin-top: 14px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.card-head h2 { font-size: 15.5px; }
.link { color: var(--brand); }

.loading { display: flex; flex-direction: column; gap: 8px; }
.mono { font-family: var(--mono); font-size: 12px; color: var(--ink-2); }
.cell-name { max-width: 180px; }

.top-list { display: flex; flex-direction: column; gap: 10px; }
.top-item { display: flex; align-items: center; gap: 10px; }
.top-img { width: 44px; flex: none; }
.top-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.top-name { font-size: 13px; }
.top-name:hover { color: var(--brand); }

.mini-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 14px; }
.mini-stats div { text-align: center; }
.mini-stats span { display: block; font-size: 12px; color: var(--muted); }
.mini-stats strong { font-size: 20px; font-variant-numeric: tabular-nums; }

@media (max-width: 1080px) {
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .grid { grid-template-columns: 1fr; }
}
@media (max-width: 560px) {
  .mini-stats { grid-template-columns: repeat(2, 1fr); }
}
</style>
