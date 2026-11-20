<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminApiClient, saveBlob } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppModal from '@/components/ui/AppModal.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusTag from '@/components/ui/StatusTag.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { dateTime, money } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const items = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const keyword = ref('')
const status = ref(route.query.status || '')

const detailOpen = ref(false)
const detail = ref(null)
const detailLoading = ref(false)
const actionOpen = ref(false)
const actionMode = ref('cancel')
const actionReason = ref('')
const busy = ref(false)

const statusOptions = ['', '待付款', '已付款', '已发货', '已完成', '退款中', '已取消']

const exportCsv = async () => {
  try {
    const res = await adminApiClient.exportCsv('orders')
    saveBlob(res.data, `campus-orders-${new Date().toISOString().slice(0, 10)}.csv`)
    toastSuccess('已导出 CSV')
  } catch (error) {
    toastError(error.message)
  }
}

const load = async (next = 1) => {
  loading.value = true
  try {
    const data = await adminApiClient.orders({
      page: next,
      per_page: 15,
      status: status.value || undefined,
      keyword: keyword.value || undefined
    })
    items.value = data.items || []
    total.value = data.total || 0
    pages.value = data.pages || 0
    page.value = data.page || 1
  } catch (error) {
    toastError(error.message)
  } finally {
    loading.value = false
  }
}

const search = () => {
  router.replace({ path: '/admin/orders', query: status.value ? { status: status.value } : {} })
  load(1)
}

const openDetail = async (order) => {
  detailOpen.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await adminApiClient.order(order.id)
  } catch (error) {
    toastError(error.message)
    detailOpen.value = false
  } finally {
    detailLoading.value = false
  }
}

const openAction = (order, mode) => {
  detail.value = order
  actionMode.value = mode
  actionReason.value = ''
  actionOpen.value = true
}

const submitAction = async () => {
  if (!actionReason.value.trim()) {
    toastError('请填写处理说明')
    return
  }
  busy.value = true
  try {
    if (actionMode.value === 'cancel') {
      await adminApiClient.cancelOrder(detail.value.id, actionReason.value.trim())
      toastSuccess('订单已取消并退款')
    } else {
      await adminApiClient.refundOrder(detail.value.id, { approve: true, note: actionReason.value.trim() })
      toastSuccess('已同意退款')
    }
    actionOpen.value = false
    detailOpen.value = false
    load(page.value)
  } catch (error) {
    toastError(error.message)
  } finally {
    busy.value = false
  }
}

const quickCancel = async (order) => {
  const ok = await confirmAction({
    title: '管理员取消订单',
    message: '取消后库存释放；余额支付的订单会原路退回余额。',
    confirmText: '取消订单'
  })
  if (!ok) return
  try {
    await adminApiClient.cancelOrder(order.id, '管理员介入取消')
    toastSuccess('订单已取消')
    load(page.value)
  } catch (error) {
    toastError(error.message)
  }
}

onMounted(() => load(1))
</script>

<template>
  <div class="admin-orders">
    <header class="head">
      <div>
        <h1>订单管理</h1>
        <p class="text-sm text-muted">共 {{ total }} 笔订单 · 可查看状态时间线并处理异常订单</p>
      </div>
      <div class="toolbar">
        <form class="search" @submit.prevent="search">
          <AppIcon name="search" :size="15" />
          <input v-model="keyword" placeholder="订单号 / 买家昵称 / 手机号" maxlength="30" />
        </form>
        <button class="btn btn-sm" type="button" @click="exportCsv">导出 CSV</button>
        <select v-model="status" class="select input-sm" @change="search">
          <option v-for="item in statusOptions" :key="item" :value="item">{{ item || '全部状态' }}</option>
        </select>
      </div>
    </header>

    <div class="panel">
      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 6" :key="i" :h="46" radius="8px" />
      </div>

      <AppEmpty v-else-if="!items.length" icon="truck" title="没有匹配的订单" compact />

      <table v-else class="table">
        <thead>
          <tr>
            <th>订单号</th>
            <th>商品</th>
            <th>买家 / 卖家</th>
            <th>金额</th>
            <th>状态</th>
            <th>时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in items" :key="order.id">
            <td class="mono">{{ order.order_no }}</td>
            <td class="ellipsis cell-name">{{ order.items?.[0]?.name || '—' }}</td>
            <td>
              <p>{{ order.buyer?.nickname }}</p>
              <p class="text-xs text-muted">卖家 {{ order.seller?.nickname }}</p>
            </td>
            <td>¥{{ money(order.total_amount) }}</td>
            <td><StatusTag :status="order.status" /></td>
            <td class="text-muted">{{ dateTime(order.created_at) }}</td>
            <td>
              <div class="table-actions">
                <button class="btn btn-sm" type="button" @click="openDetail(order)">详情</button>
                <button
                  v-if="['待付款', '已付款', '已发货'].includes(order.status)"
                  class="btn btn-sm btn-danger"
                  type="button"
                  @click="quickCancel(order)"
                >
                  取消
                </button>
                <button v-if="order.status === '退款中'" class="btn btn-sm btn-primary" type="button" @click="openDetail(order)">
                  处理退款
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="15" @change="load" />
    </div>

    <AppModal v-model="detailOpen" title="订单详情" width="720px">
      <div v-if="detailLoading" class="loading">
        <SkeletonBlock :h="40" radius="8px" />
        <SkeletonBlock :h="120" radius="8px" />
      </div>
      <template v-else-if="detail">
        <div class="detail-head">
          <span class="mono">{{ detail.order_no }}</span>
          <StatusTag :status="detail.status" />
          <span class="text-xs text-muted">{{ dateTime(detail.created_at) }}</span>
        </div>

        <div class="detail-grid">
          <div><span>买家</span><p>{{ detail.buyer?.nickname }} · {{ detail.receiver_phone }}</p></div>
          <div><span>卖家</span><p>{{ detail.seller?.nickname }}</p></div>
          <div><span>履约方式</span><p>{{ detail.delivery_type }} / {{ detail.pay_method }}</p></div>
          <div><span>交易地点</span><p>{{ detail.address_text || '—' }}</p></div>
          <div><span>实付金额</span><p class="price price-sm">¥{{ money(detail.total_amount) }}</p></div>
          <div><span>物流</span><p>{{ detail.ship_company }} {{ detail.tracking_no || '—' }}</p></div>
        </div>

        <h4 class="section-label">商品清单</h4>
        <table class="table">
          <thead><tr><th>商品</th><th>单价</th><th>数量</th><th>小计</th></tr></thead>
          <tbody>
            <tr v-for="item in detail.items" :key="item.id">
              <td>{{ item.name }}</td>
              <td>¥{{ money(item.price) }}</td>
              <td>{{ item.quantity }}</td>
              <td>¥{{ money(item.subtotal) }}</td>
            </tr>
          </tbody>
        </table>

        <h4 class="section-label">状态时间线</h4>
        <ol class="timeline">
          <li v-for="(log, index) in detail.timeline" :key="index">
            <span class="dot" />
            <div>
              <strong>{{ log.to_status }}</strong>
              <span class="text-xs text-muted"> · {{ dateTime(log.created_at) }} · {{ log.operator_type }}{{ log.operator_name ? `：${log.operator_name}` : '' }}</span>
              <p v-if="log.remark" class="text-xs text-muted">{{ log.remark }}</p>
            </div>
          </li>
        </ol>

        <div v-if="detail.refund_reason" class="alert alert-warn mt-12">
          <AppIcon name="alert" :size="15" />
          <span>退款原因：{{ detail.refund_reason }}</span>
        </div>
      </template>
      <template #footer>
        <button
          v-if="detail && detail.status === '退款中'"
          class="btn btn-primary"
          type="button"
          @click="openAction(detail, 'refund')"
        >
          同意退款
        </button>
        <button
          v-if="detail && ['待付款', '已付款', '已发货'].includes(detail.status)"
          class="btn btn-danger"
          type="button"
          @click="openAction(detail, 'cancel')"
        >
          取消订单
        </button>
        <button class="btn" type="button" @click="detailOpen = false">关闭</button>
      </template>
    </AppModal>

    <AppModal v-model="actionOpen" :title="actionMode === 'cancel' ? '取消订单' : '同意退款'" width="420px">
      <p class="text-sm">订单：<strong>{{ detail?.order_no }}</strong> · ¥{{ money(detail?.total_amount || 0) }}</p>
      <div class="field mt-12">
        <label>处理说明</label>
        <textarea v-model="actionReason" class="textarea" maxlength="100" placeholder="例如：卖家长期未发货，管理员介入取消" />
      </div>
      <template #footer>
        <button class="btn" type="button" @click="actionOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="busy" @click="submitAction">
          {{ busy ? '处理中…' : '确认' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.head h1 { font-size: 22px; }
.toolbar { display: flex; gap: 8px; flex-wrap: wrap; }
.search { display: flex; align-items: center; gap: 6px; border: 1px solid var(--line-strong); border-radius: 8px; padding: 3px 10px; background: #fff; color: var(--muted); }
.search input { border: none; outline: none; height: 28px; width: 210px; font-size: 13px; }
.loading { display: flex; flex-direction: column; gap: 8px; }
.mono { font-family: var(--mono); font-size: 12px; color: var(--ink-2); }
.cell-name { max-width: 180px; }

.detail-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding-bottom: 12px; border-bottom: 1px solid var(--line); }
.detail-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 14px; }
.detail-grid span { color: var(--muted); font-size: 11.5px; }
.detail-grid p { font-size: 13px; margin-top: 2px; }
.section-label { font-size: 13px; color: var(--muted); margin: 18px 0 8px; }
.timeline { display: flex; flex-direction: column; gap: 10px; }
.timeline li { display: flex; gap: 10px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--brand); margin-top: 6px; flex: none; }
.timeline strong { font-size: 13px; }
</style>
