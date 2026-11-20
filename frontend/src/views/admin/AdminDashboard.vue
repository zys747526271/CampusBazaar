<script setup>
import { computed, onMounted, ref } from 'vue'
import { adminApiClient } from '@/api'
import { toastError, toastSuccess } from '@/composables/useToast'
import StatCard from '@/components/ui/StatCard.vue'
import TrendChart from './components/TrendChart.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { money } from '@/utils/format'

const loading = ref(true)
const running = ref(false)
const data = ref(null)

const cards = computed(() => {
  if (!data.value) return []
  return [
    { label: '用户总数', value: data.value.users.total, hint: `今日新增 ${data.value.users.today} · 卖家 ${data.value.users.sellers}`, icon: 'user', tone: 'info' },
    { label: '在售商品', value: data.value.products.on_sale, hint: `全部 ${data.value.products.total} · 待审核 ${data.value.products.pending}`, icon: 'package', tone: 'brand' },
    { label: '订单总数', value: data.value.orders.total, hint: `今日新增 ${data.value.orders.today} 笔`, icon: 'truck', tone: 'ok' },
    { label: '累计成交额', value: `¥${money(data.value.gmv.total)}`, hint: `今日 ¥${money(data.value.gmv.today)}`, icon: 'wallet', tone: 'warn' }
  ]
})

const load = async () => {
  loading.value = true
  try {
    data.value = await adminApiClient.stats()
  } catch (error) {
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

const runJobs = async () => {
  running.value = true
  try {
    const result = await adminApiClient.runJobs()
    toastSuccess(`任务完成：超时取消 ${result.expired_orders} 笔，自动确认 ${result.auto_confirmed} 笔`)
    load()
  } catch (error) {
    toastError(error.message)
  } finally {
    running.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="dashboard">
    <header class="head">
      <div>
        <h1>控制台</h1>
        <p class="text-sm text-muted">平台运行概览与今日待办</p>
      </div>
      <div class="ops">
        <button class="btn btn-sm" type="button" :disabled="running" @click="runJobs">
          <AppIcon name="refresh" :size="14" /> {{ running ? '执行中…' : '执行定时任务' }}
        </button>
        <RouterLink to="/admin/reports" class="btn btn-sm">处理举报</RouterLink>
      </div>
    </header>

    <div v-if="loading" class="loading">
      <SkeletonBlock v-for="i in 4" :key="i" :h="88" radius="12px" />
    </div>

    <template v-else-if="data">
      <div class="stats">
        <StatCard v-for="card in cards" :key="card.label" v-bind="card" />
      </div>

      <div class="grid">
        <section class="panel">
          <div class="card-head">
            <h2>近 7 天趋势</h2>
            <span class="text-sm text-muted">订单量 / 成交额</span>
          </div>
          <TrendChart :data="data.trend" />
        </section>

        <section class="panel">
          <div class="card-head">
            <h2>今日待办</h2>
          </div>
          <ul class="todo">
            <li>
              <RouterLink to="/admin/products?status=待审核" class="todo-item">
                <span class="todo-icon warn"><AppIcon name="package" :size="16" /></span>
                <div>
                  <strong>商品待审核</strong>
                  <p class="text-xs text-muted">共 {{ data.moderation.pending_products }} 件，审核通过后才会展示</p>
                </div>
                <span class="count">{{ data.moderation.pending_products }}</span>
              </RouterLink>
            </li>
            <li>
              <RouterLink to="/admin/reports" class="todo-item">
                <span class="todo-icon danger"><AppIcon name="alert" :size="16" /></span>
                <div>
                  <strong>待处理举报</strong>
                  <p class="text-xs text-muted">违规内容需在 24 小时内处置</p>
                </div>
                <span class="count">{{ data.moderation.pending_reports }}</span>
              </RouterLink>
            </li>
            <li>
              <RouterLink to="/admin/comments" class="todo-item">
                <span class="todo-icon info"><AppIcon name="message" :size="16" /></span>
                <div>
                  <strong>全站评价</strong>
                  <p class="text-xs text-muted">可检索并隐藏违规评价</p>
                </div>
                <span class="count">{{ data.moderation.comments }}</span>
              </RouterLink>
            </li>
            <li>
              <RouterLink to="/admin/sellers" class="todo-item">
                <span class="todo-icon ok"><AppIcon name="shop" :size="16" /></span>
                <div>
                  <strong>活跃商家</strong>
                  <p class="text-xs text-muted">查看商家商品与成交情况</p>
                </div>
                <span class="count">{{ data.users.sellers }}</span>
              </RouterLink>
            </li>
          </ul>

          <div class="quick">
            <RouterLink to="/admin/tags" class="quick-link">分类管理</RouterLink>
            <RouterLink to="/admin/banners" class="quick-link">轮播配置</RouterLink>
            <RouterLink to="/admin/audit" class="quick-link">操作审计</RouterLink>
          </div>
        </section>
      </div>

      <section class="panel kpi">
        <div><span>人均订单</span><strong>{{ data.users.total ? (data.orders.total / data.users.total).toFixed(2) : '0.00' }}</strong></div>
        <div><span>动销率</span><strong>{{ data.products.total ? ((data.products.on_sale / data.products.total) * 100).toFixed(1) : '0' }}%</strong></div>
        <div><span>待审核占比</span><strong>{{ data.products.total ? ((data.products.pending / data.products.total) * 100).toFixed(1) : '0' }}%</strong></div>
        <div><span>客单价</span><strong>¥{{ data.orders.total ? money(data.gmv.total / data.orders.total) : '0.00' }}</strong></div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.head h1 { font-size: 22px; letter-spacing: -.3px; }
.ops { display: flex; gap: 8px; }
.loading { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.grid { display: grid; grid-template-columns: 1.5fr 1fr; gap: 14px; margin-top: 14px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.card-head h2 { font-size: 15.5px; }

.todo { display: flex; flex-direction: column; gap: 6px; }
.todo-item {
  display: flex; align-items: center; gap: 11px; padding: 10px; border-radius: 10px;
  transition: background .14s;
}
.todo-item:hover { background: var(--hover); }
.todo-icon {
  width: 34px; height: 34px; border-radius: 10px; flex: none;
  display: grid; place-items: center;
}
.todo-icon.warn { background: var(--warn-soft); color: var(--warn); }
.todo-icon.danger { background: var(--danger-soft); color: var(--danger); }
.todo-icon.info { background: var(--info-soft); color: var(--info); }
.todo-icon.ok { background: var(--ok-soft); color: var(--ok); }
.todo-item strong { display: block; font-size: 13.5px; }
.count { margin-left: auto; font-size: 18px; font-weight: 700; font-variant-numeric: tabular-nums; }

.quick { display: flex; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px dashed var(--line); }
.quick-link {
  flex: 1; text-align: center; padding: 8px; border-radius: 8px;
  background: #fafbfc; color: var(--ink-2); font-size: 12.5px;
}
.quick-link:hover { background: var(--brand-soft); color: var(--brand); }

.kpi { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 14px; }
.kpi div { text-align: center; }
.kpi span { display: block; font-size: 12px; color: var(--muted); }
.kpi strong { font-size: 20px; font-variant-numeric: tabular-nums; }

@media (max-width: 1100px) {
  .stats, .loading { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .grid { grid-template-columns: 1fr; }
}
@media (max-width: 560px) {
  .kpi { grid-template-columns: repeat(2, 1fr); }
}
</style>
