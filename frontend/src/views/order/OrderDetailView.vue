<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { commentApi, orderApi } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppImage from '@/components/ui/AppImage.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppRating from '@/components/ui/AppRating.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusTag from '@/components/ui/StatusTag.vue'
import { ORDER_ACTION_TEXT, dateTime, money } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const order = ref(null)
const busy = ref(false)

const refundOpen = ref(false)
const refundReason = ref('')
const commentOpen = ref(false)
const commentTarget = ref(null)
const commentForm = reactive({ rating: 5, content: '' })
const commentBusy = ref(false)

const steps = computed(() => {
  if (!order.value) return []
  const timeline = order.value.timeline || []
  return timeline.map((log) => ({
    status: log.to_status,
    time: log.created_at,
    remark: log.remark,
    operator: log.operator_name,
    type: log.operator_type
  }))
})

const statusTip = computed(() => {
  const map = {
    待付款: '订单已创建，请在 30 分钟内完成支付，超时将自动取消',
    已付款: '已付款，等待卖家发货或约定自提',
    已发货: '卖家已发货，收到商品并验货后请确认收货',
    已完成: '交易完成，货款已结算给卖家',
    已取消: '订单已取消，库存已释放',
    退款中: '退款申请处理中，请与卖家保持沟通'
  }
  return map[order.value?.status] || '订单进行中'
})

const load = async () => {
  loading.value = true
  try {
    order.value = await orderApi.detail(route.params.id)
  } catch (error) {
    toastError(error.message)
    order.value = null
  } finally {
    loading.value = false
  }
}

const act = async (action) => {
  const current = order.value
  if (!current) return

  if (action === 'pay') {
    const ok = await confirmAction({
      title: '余额支付',
      message: `将从余额扣除 ¥${money(current.total_amount)}，确认支付？`,
      confirmText: '确认支付',
      danger: false
    })
    if (!ok) return
    await run(async () => {
      await orderApi.pay(current.id)
      toastSuccess('支付成功')
    })
    return
  }
  if (action === 'confirm') {
    const ok = await confirmAction({
      title: '确认收货',
      message: '请确认已收到商品并当面验货，确认后货款结算给卖家。',
      confirmText: '确认收货',
      danger: false
    })
    if (!ok) return
    await run(async () => {
      await orderApi.confirm(current.id)
      toastSuccess('已确认收货')
    })
    return
  }
  if (action === 'cancel') {
    const ok = await confirmAction({
      title: '取消订单',
      message: '取消后库存会释放，确定继续吗？',
      confirmText: '取消订单'
    })
    if (!ok) return
    await run(async () => {
      await orderApi.cancel(current.id, '买家主动取消')
      toastSuccess('订单已取消')
    })
    return
  }
  if (action === 'refund') {
    refundReason.value = ''
    refundOpen.value = true
    return
  }
  if (action === 'cancel_refund') {
    const ok = await confirmAction({
      title: '撤销退款申请',
      message: '撤销后订单将回到退款前的状态，确定继续吗？',
      confirmText: '撤销申请',
      danger: false
    })
    if (!ok) return
    await run(async () => {
      await orderApi.cancelRefund(current.id)
      toastSuccess('已撤销退款申请')
    })
    return
  }
  if (action === 'comment') {
    const target = order.value.items.find((item) => !item.commented) || order.value.items[0]
    openComment(target)
  }
  if (action === 'confirm_offline') {
    toastSuccess('请等待卖家确认收款')
  }
}

const run = async (fn) => {
  busy.value = true
  try {
    await fn()
    await load()
  } catch (error) {
    toastError(error.message)
  } finally {
    busy.value = false
  }
}

const submitRefund = async () => {
  if (refundReason.value.trim().length < 2) {
    toastError('请填写退款原因')
    return
  }
  busy.value = true
  try {
    await orderApi.refund(order.value.id, refundReason.value.trim())
    toastSuccess('退款申请已提交，等待卖家处理')
    refundOpen.value = false
    await load()
  } catch (error) {
    toastError(error.message)
  } finally {
    busy.value = false
  }
}

const openComment = (item) => {
  commentTarget.value = item
  commentForm.rating = 5
  commentForm.content = ''
  commentOpen.value = true
}

const submitComment = async () => {
  if (!commentTarget.value) return
  commentBusy.value = true
  try {
    await commentApi.create({
      order_id: order.value.id,
      product_id: commentTarget.value.product_id,
      rating: commentForm.rating,
      content: commentForm.content
    })
    toastSuccess('评价成功，感谢你的反馈')
    commentOpen.value = false
    await load()
  } catch (error) {
    toastError(error.message)
  } finally {
    commentBusy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="order-detail">
    <div v-if="loading" class="panel loading">
      <SkeletonBlock :h="24" w="220px" />
      <SkeletonBlock :h="120" radius="10px" />
      <SkeletonBlock :h="140" radius="10px" />
    </div>

    <AppEmpty v-else-if="!order" icon="file-text" title="订单不存在" description="订单可能已被删除">
      <RouterLink to="/orders" class="btn btn-primary btn-sm">返回订单列表</RouterLink>
    </AppEmpty>

    <template v-else>
      <button class="back" type="button" @click="router.back()">
        <AppIcon name="arrow-left" :size="15" /> 返回
      </button>

      <section class="panel status-panel">
        <div class="status-head">
          <div>
            <div class="status-line">
              <StatusTag :status="order.status" />
              <span class="text-sm text-muted">订单号 {{ order.order_no }}</span>
            </div>
            <p class="status-tip">{{ statusTip }}</p>
          </div>
          <div class="ops">
            <button
              v-for="action in order.actions"
              :key="action"
              class="btn btn-sm"
              :class="{ 'btn-primary': ['pay', 'confirm'].includes(action) }"
              type="button"
              :disabled="busy"
              @click="act(action)"
            >
              {{ ORDER_ACTION_TEXT[action] || action }}
            </button>
          </div>
        </div>

        <ol class="timeline">
          <li v-for="(step, index) in steps" :key="index" class="step">
            <span class="dot" :class="{ last: index === steps.length - 1 }" />
            <div class="step-body">
              <strong>{{ step.status }}</strong>
              <span class="text-xs text-muted">{{ dateTime(step.time) }} · {{ step.operator || step.type }}</span>
              <p v-if="step.remark" class="text-xs remark">{{ step.remark }}</p>
            </div>
          </li>
        </ol>
      </section>

      <section class="panel">
        <h2 class="block-title">交易信息</h2>
        <div class="info-grid">
          <div><span>联系人</span><p>{{ order.receiver_name }}</p></div>
          <div><span>联系电话</span><p>{{ order.receiver_phone }}</p></div>
          <div><span>履约方式</span><p>{{ order.delivery_type }}</p></div>
          <div><span>支付方式</span><p>{{ order.pay_method }}</p></div>
          <div class="wide"><span>交易地点 / 地址</span><p>{{ order.address_text || '校内面交，具体地点与卖家沟通' }}</p></div>
          <div v-if="order.ship_company || order.tracking_no" class="wide">
            <span>物流信息</span><p>{{ order.ship_company }} {{ order.tracking_no }}</p>
          </div>
          <div v-if="order.remark" class="wide"><span>买家备注</span><p>{{ order.remark }}</p></div>
          <div v-if="order.cancel_reason" class="wide"><span>取消原因</span><p>{{ order.cancel_reason }}</p></div>
          <div v-if="order.refund_reason" class="wide"><span>退款原因</span><p>{{ order.refund_reason }}</p></div>
        </div>
      </section>

      <section class="panel">
        <div class="block-head">
          <h2 class="block-title">商品清单</h2>
          <RouterLink v-if="order.seller" :to="`/shops/${order.seller.id}`" class="text-sm link">
            卖家：{{ order.seller.nickname }}
          </RouterLink>
        </div>
        <ul class="items">
          <li v-for="item in order.items" :key="item.id" class="item">
            <RouterLink :to="`/products/${item.product_id}`" class="thumb">
              <AppImage :src="item.image" :alt="item.name" radius="9px" />
            </RouterLink>
            <div class="item-info">
              <RouterLink :to="`/products/${item.product_id}`" class="item-name clamp-2">{{ item.name }}</RouterLink>
              <p class="text-xs text-muted">{{ item.condition }} · × {{ item.quantity }}</p>
            </div>
            <div class="item-price">
              <span class="price price-sm"><span class="unit">¥</span>{{ money(item.price) }}</span>
              <span class="text-xs text-muted">小计 ¥{{ money(item.subtotal) }}</span>
            </div>
            <div class="item-ops">
              <button
                v-if="order.status === '已完成' && !item.commented"
                class="btn btn-sm btn-ghost"
                type="button"
                @click="openComment(item)"
              >
                去评价
              </button>
              <span v-else-if="order.status === '已完成'" class="tag tag-ok">已评价</span>
            </div>
          </li>
        </ul>

        <div class="amounts">
          <div class="row"><span>商品金额</span><span>¥{{ money(order.items_total) }}</span></div>
          <div class="row"><span>运费</span><span>{{ order.shipping_fee ? `¥${money(order.shipping_fee)}` : '¥0.00（校内自提）' }}</span></div>
          <div class="row total"><span>实付金额</span><span class="price price-md"><span class="unit">¥</span>{{ money(order.total_amount) }}</span></div>
        </div>
      </section>

      <p class="foot-note">
        订单创建于 {{ dateTime(order.created_at) }}
        <template v-if="order.paid_at"> · 支付于 {{ dateTime(order.paid_at) }}</template>
        <template v-if="order.finished_at"> · 完成于 {{ dateTime(order.finished_at) }}</template>
      </p>
    </template>

    <AppModal v-model="refundOpen" title="申请退款" width="440px">
      <div class="field">
        <label>退款原因</label>
        <textarea v-model="refundReason" class="textarea" maxlength="100" placeholder="例如：商品与描述不符 / 卖家无法按约履约" />
      </div>
      <div class="alert alert-warn mt-12">
        <AppIcon name="alert" :size="15" />
        提交后订单进入「退款中」，卖家同意后自动退款；线下支付请与卖家线下结算。
      </div>
      <template #footer>
        <button class="btn" type="button" @click="refundOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="busy" @click="submitRefund">提交申请</button>
      </template>
    </AppModal>

    <AppModal v-model="commentOpen" title="评价商品" width="460px">
      <div v-if="commentTarget" class="comment-target">
        <AppImage :src="commentTarget.image" :alt="commentTarget.name" radius="8px" class="ct-img" />
        <span class="clamp-2">{{ commentTarget.name }}</span>
      </div>
      <div class="field mt-16">
        <label>评分</label>
        <AppRating v-model="commentForm.rating" :size="24" interactive show-value />
      </div>
      <div class="field mt-12">
        <label>评价内容（选填）</label>
        <textarea v-model="commentForm.content" class="textarea" maxlength="500" placeholder="描述商品成色、卖家沟通与履约体验" />
      </div>
      <template #footer>
        <button class="btn" type="button" @click="commentOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="commentBusy" @click="submitComment">
          {{ commentBusy ? '提交中…' : '发布评价' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.order-detail { display: flex; flex-direction: column; gap: 14px; }
.loading { display: flex; flex-direction: column; gap: 14px; }
.back { display: inline-flex; align-items: center; gap: 5px; border: none; background: none; color: var(--muted); font-size: 13px; padding: 0; }
.back:hover { color: var(--brand); }

.status-panel { padding: 20px 22px; }
.status-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.status-line { display: flex; align-items: center; gap: 10px; }
.status-tip { margin-top: 8px; color: var(--ink-2); font-size: 13.5px; }
.ops { display: flex; gap: 8px; flex-wrap: wrap; }

.timeline { display: flex; gap: 0; margin-top: 20px; padding-top: 18px; border-top: 1px dashed var(--line); overflow-x: auto; }
.step { position: relative; flex: 1; min-width: 140px; padding-right: 12px; }
.step:last-child { flex: 0 0 auto; }
.dot {
  display: block; width: 9px; height: 9px; border-radius: 50%;
  background: var(--line-strong); margin-bottom: 10px; position: relative;
}
.dot::after {
  content: ''; position: absolute; left: 12px; top: 4px;
  width: calc(100% + 120px); height: 1px; background: var(--line);
}
.step:last-child .dot::after { display: none; }
.dot.last { background: var(--brand); box-shadow: 0 0 0 4px rgba(255, 80, 0, .14); }
.step-body { display: flex; flex-direction: column; gap: 2px; }
.step-body strong { font-size: 13px; }
.remark { color: var(--muted); margin-top: 2px; }

.block-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.block-title { font-size: 16px; }
.link { color: var(--brand); }

.info-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 14px; }
.info-grid > div { min-width: 0; }
.info-grid .wide { grid-column: 1 / -1; }
.info-grid span { color: var(--muted); font-size: 12px; }
.info-grid p { margin-top: 3px; font-size: 13.5px; }

.items { display: flex; flex-direction: column; margin-top: 12px; }
.item { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--line); }
.item:last-child { border-bottom: none; }
.thumb { width: 76px; flex: none; }
.item-info { flex: 1; min-width: 0; }
.item-name { font-size: 13.5px; }
.item-name:hover { color: var(--brand); }
.item-price { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
.item-ops { width: 96px; display: flex; justify-content: flex-end; }

.amounts { border-top: 1px dashed var(--line); margin-top: 8px; padding-top: 14px; display: flex; flex-direction: column; gap: 6px; align-items: flex-end; }
.amounts .row { display: flex; gap: 24px; font-size: 13px; color: var(--ink-2); }
.amounts .total { padding-top: 6px; font-size: 14px; color: var(--ink); }

.foot-note { color: var(--muted); font-size: 12px; text-align: right; }

.comment-target { display: flex; align-items: center; gap: 10px; background: #fafbfc; padding: 10px; border-radius: 10px; font-size: 13px; }
.ct-img { width: 52px; flex: none; }

@media (max-width: 880px) {
  .info-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .item { flex-wrap: wrap; }
  .item-ops { width: auto; }
}
</style>
