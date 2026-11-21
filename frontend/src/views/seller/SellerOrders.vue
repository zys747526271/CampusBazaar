<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { sellerApi } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import PageHeader from '@/components/ui/PageHeader.vue'
import AppTabs from '@/components/ui/AppTabs.vue'
import AppImage from '@/components/ui/AppImage.vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusTag from '@/components/ui/StatusTag.vue'
import { dateTime, money } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const items = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const status = ref(route.query.status || '')
const keyword = ref('')
const busyId = ref(0)

const shipOpen = ref(false)
const shipTarget = ref(null)
const shipForm = reactive({ ship_company: '', tracking_no: '', note: '' })
const shipBusy = ref(false)

const pickupOpen = ref(false)
const pickupTarget = ref(null)
const pickupLocation = ref('')
const pickupBusy = ref(false)

const refundOpen = ref(false)
const refundTarget = ref(null)
const refundForm = reactive({ approve: true, note: '' })
const refundBusy = ref(false)

const tabs = [
  { label: '全部', value: '' },
  { label: '待付款', value: '待付款' },
  { label: '待发货', value: '已付款' },
  { label: '已发货', value: '已发货' },
  { label: '退款中', value: '退款中' },
  { label: '已完成', value: '已完成' }
]

const needTracking = computed(() => shipTarget.value?.delivery_type === '快递')

const load = async (next = 1) => {
  loading.value = true
  try {
    const data = await sellerApi.orders({ page: next, per_page: 10, status: status.value || undefined, keyword: keyword.value || undefined })
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

const changeTab = (value) => {
  status.value = value
  router.replace({ path: '/seller/orders', query: value ? { status: value } : {} })
  load(1)
}

const openPickup = (order) => {
  pickupTarget.value = order
  pickupLocation.value = order.pickup_location || ''
  pickupOpen.value = true
}

const submitPickup = async () => {
  if (pickupLocation.value.trim().length < 2) {
    toastError('请填写具体自提点')
    return
  }
  pickupBusy.value = true
  try {
    await sellerApi.setPickupLocation(pickupTarget.value.id, pickupLocation.value.trim())
    toastSuccess('自提点已保存，买家会收到通知')
    pickupOpen.value = false
    load(page.value)
  } catch (error) {
    toastError(error.message)
  } finally {
    pickupBusy.value = false
  }
}

const openShip = (order) => {
  shipTarget.value = order
  shipForm.ship_company = ''
  shipForm.tracking_no = ''
  shipForm.note = ''
  shipOpen.value = true
}

const submitShip = async () => {
  if (needTracking.value && (!shipForm.ship_company.trim() || !shipForm.tracking_no.trim())) {
    toastError('快递发货请填写快递公司与单号')
    return
  }
  shipBusy.value = true
  try {
    await sellerApi.ship(shipTarget.value.id, { ...shipForm })
    toastSuccess('发货成功')
    shipOpen.value = false
    load(page.value)
  } catch (error) {
    toastError(error.message)
  } finally {
    shipBusy.value = false
  }
}

const confirmPaid = async (order) => {
  const ok = await confirmAction({
    title: '确认收款',
    message: `确认已收到买家线下支付的 ¥${money(order.total_amount)}？确认后订单进入待发货。`,
    confirmText: '确认收款',
    danger: false
  })
  if (!ok) return
  busyId.value = order.id
  try {
    await sellerApi.confirmPaid(order.id)
    toastSuccess('已确认收款')
    load(page.value)
  } catch (error) {
    toastError(error.message)
  } finally {
    busyId.value = 0
  }
}

const closeOrder = async (order) => {
  const ok = await confirmAction({
    title: '关闭订单',
    message: '关闭后库存会释放，买家需要重新下单。确定继续吗？',
    confirmText: '关闭订单'
  })
  if (!ok) return
  busyId.value = order.id
  try {
    await sellerApi.closeOrder(order.id, '卖家关闭订单')
    toastSuccess('订单已关闭')
    load(page.value)
  } catch (error) {
    toastError(error.message)
  } finally {
    busyId.value = 0
  }
}

const openRefund = (order, approve) => {
  refundTarget.value = order
  refundForm.approve = approve
  refundForm.note = ''
  refundOpen.value = true
}

const submitRefund = async () => {
  refundBusy.value = true
  try {
    await sellerApi.handleRefund(refundTarget.value.id, { ...refundForm })
    toastSuccess(refundForm.approve ? '已同意退款' : '已驳回退款')
    refundOpen.value = false
    load(page.value)
  } catch (error) {
    toastError(error.message)
  } finally {
    refundBusy.value = false
  }
}

onMounted(() => load(1))
</script>

<template>
  <div class="seller-orders">
    <PageHeader title="收到的订单" subtitle="及时确认收款与发货，履约越快评价越好">
      <template #actions>
        <form class="search" @submit.prevent="load(1)">
          <input v-model="keyword" placeholder="订单号搜索" maxlength="24" />
          <button class="btn btn-sm" type="submit">搜索</button>
        </form>
      </template>
    </PageHeader>

    <div class="panel">
      <AppTabs :items="tabs" :model-value="status" @change="changeTab" />

      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 5" :key="i" :h="56" radius="8px" />
      </div>

      <AppEmpty v-else-if="!items.length" icon="truck" title="还没有订单" description="商品上架后，买家下单会出现在这里" compact />

      <table v-else class="table">
        <thead>
          <tr>
            <th>订单 / 商品</th>
            <th>买家</th>
            <th>金额</th>
            <th>状态</th>
            <th>时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in items" :key="order.id">
            <td>
              <div class="order-cell">
                <AppImage :src="order.items?.[0]?.image" :alt="order.items?.[0]?.name" radius="8px" class="thumb" />
                <div class="o-info">
                  <p class="o-no">{{ order.order_no }}</p>
                  <p class="o-name clamp-2">{{ order.items?.[0]?.name }}<span v-if="order.items?.length > 1"> 等 {{ order.items.length }} 件</span></p>
                  <p class="text-xs text-muted">
                    {{ order.delivery_type }} · {{ order.pay_method }}
                    <template v-if="order.is_pickup"> · 自提点：{{ order.pickup_location || '待补充' }}</template>
                    <template v-if="order.is_pickup && order.pickup_time"> · {{ dateTime(order.pickup_time) }}</template>
                  </p>
                  <p v-if="order.needs_pickup_location" class="text-xs text-danger mt-4">买家在等自提点</p>
                </div>
              </div>
            </td>
            <td>
              <p>{{ order.buyer?.nickname }}</p>
              <p class="text-xs text-muted">{{ order.receiver_phone }}</p>
            </td>
            <td><span class="price price-sm"><span class="unit">¥</span>{{ money(order.total_amount) }}</span></td>
            <td>
              <StatusTag :status="order.status" />
              <p v-if="order.refund_reason" class="text-xs text-danger mt-4">退款：{{ order.refund_reason }}</p>
            </td>
            <td class="text-muted">{{ dateTime(order.created_at) }}</td>
            <td>
              <div class="table-actions">
                <button
                  v-if="order.actions.includes('confirm_paid') || (order.status === '待付款' && order.pay_method === '线下')"
                  class="btn btn-sm btn-primary"
                  type="button"
                  :disabled="busyId === order.id"
                  @click="confirmPaid(order)"
                >
                  确认收款
                </button>
                <button
                  v-if="order.needs_pickup_location && (order.status === '待付款' || order.status === '已付款')"
                  class="btn btn-sm btn-primary"
                  type="button"
                  @click="openPickup(order)"
                >
                  填自提点
                </button>
                <button
                  v-if="order.status === '已付款'"
                  class="btn btn-sm btn-primary"
                  type="button"
                  :disabled="busyId === order.id"
                  @click="openShip(order)"
                >
                  {{ order.is_pickup ? '备货完成' : '发货' }}
                </button>
                <button
                  v-if="order.status === '退款中'"
                  class="btn btn-sm"
                  type="button"
                  @click="openRefund(order, true)"
                >
                  同意退款
                </button>
                <button
                  v-if="order.status === '退款中'"
                  class="btn btn-sm btn-danger"
                  type="button"
                  @click="openRefund(order, false)"
                >
                  驳回
                </button>
                <button
                  v-if="order.status === '待付款'"
                  class="btn btn-sm"
                  type="button"
                  :disabled="busyId === order.id"
                  @click="closeOrder(order)"
                >
                  关闭
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="10" @change="load" />
    </div>

    <AppModal v-model="shipOpen" title="订单发货" width="440px">
      <div v-if="shipTarget" class="ship-info">
        <p class="text-sm"><strong>{{ shipTarget.order_no }}</strong> · {{ shipTarget.delivery_type }}</p>
        <p class="text-sm text-muted">{{ shipTarget.receiver_name }} {{ shipTarget.receiver_phone }}</p>
        <p class="text-sm text-muted">{{ shipTarget.address_text }}</p>
      </div>
      <template v-if="needTracking">
        <div class="field mt-12">
          <label>快递公司</label>
          <input v-model="shipForm.ship_company" class="input" maxlength="40" placeholder="例如：顺丰 / 中通" />
        </div>
        <div class="field mt-12">
          <label>快递单号</label>
          <input v-model="shipForm.tracking_no" class="input" maxlength="60" placeholder="填写快递单号" />
        </div>
      </template>
      <div class="field mt-12">
        <label>{{ needTracking ? '发货备注' : '取货说明' }}</label>
        <input v-model="shipForm.note" class="input" maxlength="100" :placeholder="needTracking ? '例如：今天下午发出' : '例如：已备好，随时可来取'" />
      </div>
      <template #footer>
        <button class="btn" type="button" @click="shipOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="shipBusy" @click="submitShip">
          {{ shipBusy ? '提交中…' : '确认发货' }}
        </button>
      </template>
    </AppModal>

    <AppModal v-model="pickupOpen" title="填写自提点" width="440px">
      <div v-if="pickupTarget" class="ship-info">
        <p class="text-sm"><strong>{{ pickupTarget.order_no }}</strong> · 买家 {{ pickupTarget.buyer?.nickname }}</p>
        <p class="text-sm text-muted">买家下单时商品未填自提点，补充后系统会推送站内消息给买家。</p>
      </div>
      <div class="field mt-12">
        <label>自提点</label>
        <input v-model="pickupLocation" class="input" maxlength="120" placeholder="例如：图书馆一楼大厅 / 3 号宿舍楼下" />
        <span class="field-hint">写清楼栋与碰面位置，减少来回沟通</span>
      </div>
      <template #footer>
        <button class="btn" type="button" @click="pickupOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="pickupBusy" @click="submitPickup">
          {{ pickupBusy ? '保存中…' : '保存并通知买家' }}
        </button>
      </template>
    </AppModal>

    <AppModal v-model="refundOpen" :title="refundForm.approve ? '同意退款' : '驳回退款'" width="440px">
      <div v-if="refundTarget" class="alert alert-warn">
        <span>买家申请退款：{{ refundTarget.refund_reason }}</span>
      </div>
      <div class="field mt-12">
        <label>处理说明</label>
        <textarea v-model="refundForm.note" class="textarea" maxlength="200" :placeholder="refundForm.approve ? '例如：商品已收回，同意退款' : '例如：商品已按描述交付，不符合退款条件'" />
      </div>
      <template #footer>
        <button class="btn" type="button" @click="refundOpen = false">取消</button>
        <button class="btn" :class="refundForm.approve ? 'btn-primary' : 'btn-danger'" type="button" :disabled="refundBusy" @click="submitRefund">
          {{ refundBusy ? '处理中…' : refundForm.approve ? '确认退款' : '确认驳回' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.search { display: flex; align-items: center; gap: 6px; border: 1px solid var(--line-strong); border-radius: 8px; padding: 3px 4px 3px 10px; }
.search input { border: none; outline: none; height: 26px; width: 150px; font-size: 13px; }
.loading { display: flex; flex-direction: column; gap: 8px; padding-top: 8px; }

.order-cell { display: flex; align-items: center; gap: 10px; min-width: 240px; }
.thumb { width: 48px; flex: none; }
.o-info { min-width: 0; }
.o-no { font-family: var(--mono); font-size: 11.5px; color: var(--muted); }
.o-name { font-size: 13px; }
.mt-4 { margin-top: 4px; }
.ship-info { background: #fafbfc; border-radius: 8px; padding: 10px 12px; display: flex; flex-direction: column; gap: 3px; }
</style>
