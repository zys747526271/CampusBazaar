<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { addressApi, balanceApi, cartApi, orderApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppImage from '@/components/ui/AppImage.vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import { DELIVERY_LIST, PAY_LIST, money } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const cartStore = useCartStore()

const source = computed(() => (route.query.product_id ? 'now' : 'cart'))
const loading = ref(true)
const submitting = ref(false)
const errorMessage = ref('')

const lines = ref([])
const totals = ref({ items_total: 0, shipping_fee: 0, total_amount: 0, count: 0 })
const addresses = ref([])
const balance = ref({ amount: 0, recharge_enabled: false })

const form = reactive({
  addressId: 0,
  deliveryType: '面交',
  payMethod: '线下',
  remark: '',
  receiverName: auth.user?.nickname || '',
  receiverPhone: auth.user?.phone || '',
  addressText: ''
})

const addressOpen = ref(false)
const addressBusy = ref(false)
const addressForm = reactive({ name: '', phone: '', campus_area: '', detail: '', is_default: false })
const addressErrors = reactive({})

const nowItem = computed(() => ({
  product_id: Number(route.query.product_id || 0),
  quantity: Math.max(Number(route.query.quantity || 1), 1)
}))

const selectedAddress = computed(() => addresses.value.find((item) => item.id === form.addressId) || null)
const needAddress = computed(() => form.deliveryType === '快递')
const addressText = computed(() => {
  if (needAddress.value && selectedAddress.value) {
    return `${selectedAddress.value.campus_area} ${selectedAddress.value.detail}`.trim()
  }
  return form.addressText || (selectedAddress.value ? `${selectedAddress.value.campus_area} ${selectedAddress.value.detail}`.trim() : '')
})

const canPayByBalance = computed(() => Number(balance.value.amount) >= Number(totals.value.total_amount))
const receiverName = computed(() => selectedAddress.value?.name || form.receiverName)
const receiverPhone = computed(() => selectedAddress.value?.phone || form.receiverPhone)

const loadAddresses = async () => {
  try {
    const data = await addressApi.list()
    addresses.value = data.items || []
    const preferred = addresses.value.find((item) => item.is_default) || addresses.value[0]
    if (preferred && !form.addressId) form.addressId = preferred.id
  } catch (error) {
    addresses.value = []
  }
}

const loadBalance = async () => {
  try {
    balance.value = await balanceApi.info()
  } catch (error) {
    balance.value = { amount: 0, recharge_enabled: false }
  }
}

const loadSource = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    if (source.value === 'now') {
      const data = await orderApi.preview({ source: 'now', items: [{ ...nowItem.value }], pay_method: form.payMethod, delivery_type: form.deliveryType })
      lines.value = (data.groups || []).flatMap((group) =>
        group.items.map((item) => ({ ...item, seller_name: group.seller_name }))
      )
      totals.value = {
        items_total: data.items_total,
        shipping_fee: data.shipping_fee,
        total_amount: data.total_amount,
        count: lines.value.reduce((sum, item) => sum + item.quantity, 0)
      }
    } else {
      const data = await cartApi.checkout()
      lines.value = (data.groups || []).flatMap((group) =>
        group.items.map((item) => ({
          product_id: item.product.id,
          name: item.product.name,
          image: item.product.cover_image,
          price: item.product.price,
          quantity: item.quantity,
          subtotal: item.subtotal,
          cart_id: item.id,
          seller_name: group.seller.nickname
        }))
      )
      const summary = data.summary
      totals.value = {
        items_total: summary.selected_amount,
        shipping_fee: 0,
        total_amount: summary.selected_amount,
        count: summary.selected_count
      }
    }
  } catch (error) {
    errorMessage.value = error.message || '结算信息加载失败'
  } finally {
    loading.value = false
  }
}

const saveAddress = async () => {
  Object.keys(addressErrors).forEach((key) => delete addressErrors[key])
  if (!addressForm.name.trim()) addressErrors.name = '请填写联系人'
  if (!/^1[3-9]\d{9}$/.test(addressForm.phone)) addressErrors.phone = '请填写 11 位手机号'
  if (addressForm.detail.trim().length < 2) addressErrors.detail = '请填写详细地址'
  if (Object.keys(addressErrors).length) return

  addressBusy.value = true
  try {
    const created = await addressApi.create({ ...addressForm })
    toastSuccess('地址已保存')
    addressOpen.value = false
    await loadAddresses()
    form.addressId = created.id
  } catch (error) {
    Object.assign(addressErrors, error.details || {})
    toastError(error.message)
  } finally {
    addressBusy.value = false
  }
}

const submit = async () => {
  if (!lines.value.length) return
  if (!receiverName.value || !receiverPhone.value) {
    toastError('请填写联系人与联系电话')
    return
  }
  if (needAddress.value && !addressText.value) {
    toastError('快递发货需要填写收货地址')
    return
  }
  if (form.payMethod === '余额' && !canPayByBalance.value) {
    toastError('余额不足，请先充值或改用线下支付')
    return
  }

  submitting.value = true
  const payload = {
    source: source.value,
    pay_method: form.payMethod,
    delivery_type: form.deliveryType,
    remark: form.remark
  }
  if (source.value === 'now') payload.items = [{ ...nowItem.value }]
  if (form.addressId && selectedAddress.value) {
    payload.address_id = form.addressId
  } else {
    payload.receiver_name = form.receiverName
    payload.receiver_phone = form.receiverPhone
    payload.address_text = addressText.value
  }

  try {
    const data = await orderApi.create(payload)
    const orders = data.orders || []
    if (form.payMethod === '余额') {
      for (const order of orders) {
        try {
          await orderApi.pay(order.id)
        } catch (payError) {
          toastError(`订单 ${order.order_no} 支付失败：${payError.message}`)
        }
      }
      toastSuccess('下单成功，已使用余额支付')
    } else {
      toastSuccess('下单成功，等待卖家确认收款')
    }
    cartStore.refresh()
    if (orders.length === 1) router.replace(`/orders/${orders[0].id}`)
    else router.replace('/orders')
  } catch (error) {
    toastError(error.message)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadAddresses(), loadBalance()])
  await loadSource()
})
</script>

<template>
  <div class="container checkout-page">
    <header class="page-head">
      <h1>确认订单</h1>
      <RouterLink to="/cart" class="text-sm text-muted link">返回购物车</RouterLink>
    </header>

    <div v-if="loading" class="panel loading">
      <SkeletonBlock :h="120" radius="10px" />
      <SkeletonBlock :h="200" radius="10px" />
    </div>

    <AppEmpty
      v-else-if="errorMessage"
      icon="cart"
      title="结算信息加载失败"
      :description="errorMessage"
    >
      <RouterLink to="/cart" class="btn btn-primary btn-sm">返回购物车</RouterLink>
    </AppEmpty>

    <div v-else class="layout">
      <div class="main">
        <!-- 联系方式 / 地址 -->
        <section class="panel">
          <div class="panel-head">
            <h2>交易信息</h2>
            <button class="btn-text" type="button" @click="addressOpen = true">+ 新增地址</button>
          </div>

          <div v-if="addresses.length" class="address-list">
            <button
              v-for="address in addresses"
              :key="address.id"
              type="button"
              class="address"
              :class="{ on: form.addressId === address.id }"
              @click="form.addressId = address.id"
            >
              <div class="addr-top">
                <strong>{{ address.name }}</strong>
                <span>{{ address.phone }}</span>
                <span v-if="address.is_default" class="tag tag-brand">默认</span>
              </div>
              <p class="text-sm text-muted">{{ address.campus_area }} {{ address.detail }}</p>
            </button>
          </div>

          <div class="fields-grid">
            <div class="field">
              <label>联系人</label>
              <input v-model="form.receiverName" class="input" maxlength="30" placeholder="你的称呼" />
            </div>
            <div class="field">
              <label>联系电话</label>
              <input v-model="form.receiverPhone" class="input" maxlength="11" inputmode="numeric" placeholder="11 位手机号" />
            </div>
            <div class="field field-wide">
              <label>交易地点 / 收货地址</label>
              <input
                v-model="form.addressText"
                class="input"
                maxlength="200"
                :placeholder="needAddress ? '快递发货需要详细地址' : '例如：图书馆一楼大厅、3 号宿舍楼下'"
              />
            </div>
          </div>

          <div class="field mt-16">
            <label>履约方式</label>
            <div class="choice-row">
              <button
                v-for="item in DELIVERY_LIST"
                :key="item"
                type="button"
                class="choice"
                :class="{ on: form.deliveryType === item }"
                @click="form.deliveryType = item"
              >
                {{ item }}
              </button>
            </div>
            <p class="field-hint">校内交易推荐「面交」，当面验货更安心；快递需卖家填写单号。</p>
          </div>
        </section>

        <!-- 商品清单 -->
        <section class="panel">
          <div class="panel-head">
            <h2>商品清单</h2>
            <span class="text-sm text-muted">共 {{ totals.count }} 件</span>
          </div>
          <ul class="lines">
            <li v-for="item in lines" :key="item.product_id" class="line">
              <AppImage :src="item.image" :alt="item.name" radius="9px" class="line-img" />
              <div class="line-info">
                <p class="line-name clamp-2">{{ item.name }}</p>
                <p class="text-xs text-muted">卖家：{{ item.seller_name }}</p>
              </div>
              <div class="line-price">
                <span class="price price-sm"><span class="unit">¥</span>{{ money(item.price) }}</span>
                <span class="text-xs text-muted">× {{ item.quantity }}</span>
              </div>
              <div class="line-sub price price-sm"><span class="unit">¥</span>{{ money(item.subtotal) }}</div>
            </li>
          </ul>
        </section>

        <!-- 支付方式 -->
        <section class="panel">
          <div class="panel-head">
            <h2>支付方式</h2>
            <RouterLink v-if="balance.recharge_enabled" to="/balance" class="text-sm link">去充值</RouterLink>
          </div>
          <div class="pay-list">
            <button
              v-for="item in PAY_LIST"
              :key="item"
              type="button"
              class="pay"
              :class="{ on: form.payMethod === item }"
              @click="form.payMethod = item"
            >
              <span class="pay-icon" :class="item === '余额' ? 'balance' : 'offline'">
                <AppIcon :name="item === '余额' ? 'wallet' : 'shop'" :size="17" />
              </span>
              <div class="pay-text">
                <strong>{{ item === '余额' ? '余额支付' : '线下支付' }}</strong>
                <small v-if="item === '余额'">
                  当前余额 ¥{{ money(balance.amount) }}
                  <span v-if="!canPayByBalance" class="text-danger">（不足）</span>
                </small>
                <small v-else>当面付款，卖家确认收款后进入发货</small>
              </div>
              <span class="radio" :class="{ on: form.payMethod === item }" />
            </button>
          </div>

          <div class="field mt-16">
            <label>订单备注（选填）</label>
            <textarea v-model="form.remark" class="textarea" maxlength="200" placeholder="例如：晚上 7 点后图书馆门口交易" />
          </div>
        </section>
      </div>

      <aside class="side">
        <div class="summary panel">
          <h3>订单金额</h3>
          <div class="sum-row"><span>商品金额</span><span>¥{{ money(totals.items_total) }}</span></div>
          <div class="sum-row"><span>运费</span><span>{{ totals.shipping_fee ? `¥${money(totals.shipping_fee)}` : '校内自提免运费' }}</span></div>
          <div class="sum-row total"><span>应付金额</span><span class="price price-md"><span class="unit">¥</span>{{ money(totals.total_amount) }}</span></div>
          <div class="sum-tip">
            <AppIcon name="shield" :size="14" />
            <span>确认收货前，余额支付的货款由平台记账，交易纠纷可申诉。</span>
          </div>
          <button class="btn btn-primary btn-lg btn-block" type="button" :disabled="submitting || !lines.length" @click="submit">
            {{ submitting ? '提交中…' : '提交订单' }}
          </button>
          <p class="text-xs text-muted center mt-8">提交即表示同意《校园集市交易规则》</p>
        </div>
      </aside>
    </div>

    <AppModal v-model="addressOpen" title="新增地址" width="460px">
      <div class="fields-grid">
        <div class="field">
          <label>联系人</label>
          <input v-model="addressForm.name" class="input" :class="{ 'has-error': addressErrors.name }" maxlength="30" />
          <span v-if="addressErrors.name" class="field-error">{{ addressErrors.name }}</span>
        </div>
        <div class="field">
          <label>手机号</label>
          <input v-model="addressForm.phone" class="input" :class="{ 'has-error': addressErrors.phone }" maxlength="11" inputmode="numeric" />
          <span v-if="addressErrors.phone" class="field-error">{{ addressErrors.phone }}</span>
        </div>
        <div class="field field-wide">
          <label>校区 / 区域</label>
          <input v-model="addressForm.campus_area" class="input" maxlength="60" placeholder="例如：东校区 3 号楼" />
        </div>
        <div class="field field-wide">
          <label>详细地址</label>
          <input v-model="addressForm.detail" class="input" :class="{ 'has-error': addressErrors.detail }" maxlength="200" placeholder="楼栋 / 门牌 / 自提点" />
          <span v-if="addressErrors.detail" class="field-error">{{ addressErrors.detail }}</span>
        </div>
      </div>
      <label class="check mt-12"><input v-model="addressForm.is_default" type="checkbox" /> 设为默认地址</label>
      <template #footer>
        <button class="btn" type="button" @click="addressOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="addressBusy" @click="saveAddress">
          {{ addressBusy ? '保存中…' : '保存' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.checkout-page { padding-top: 22px; }
.page-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 16px; }
.page-head .link { margin-left: 4px; }
.page-head h1 { font-size: 24px; letter-spacing: -.4px; }
.link { color: var(--brand); }

.layout { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 16px; align-items: start; }
.main { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.loading { display: flex; flex-direction: column; gap: 14px; }

.panel-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.panel-head h2 { font-size: 16px; }

.address-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-bottom: 16px; }
.address {
  text-align: left; border: 1px solid var(--line-strong); background: #fff;
  border-radius: 10px; padding: 12px 14px; transition: all .16s;
}
.address:hover { border-color: var(--brand); }
.address.on { border-color: var(--brand); background: var(--brand-soft); }
.addr-top { display: flex; align-items: center; gap: 8px; font-size: 13.5px; margin-bottom: 4px; flex-wrap: wrap; }
.addr-top span { color: var(--muted); font-size: 12.5px; }

.fields-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.field-wide { grid-column: 1 / -1; }

.choice-row { display: flex; gap: 8px; flex-wrap: wrap; }
.choice {
  border: 1px solid var(--line-strong); background: #fff; color: var(--ink-2);
  border-radius: 9px; padding: 8px 20px; font-size: 13.5px;
}
.choice:hover { border-color: var(--brand); color: var(--brand); }
.choice.on { border-color: var(--brand); background: var(--brand-soft); color: var(--brand); font-weight: 600; }

.lines { display: flex; flex-direction: column; }
.line { display: flex; align-items: center; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--line); }
.line:last-child { border-bottom: none; }
.line-img { width: 72px; flex: none; }
.line-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.line-name { font-size: 13.5px; }
.line-price { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
.line-sub { width: 88px; text-align: right; font-weight: 700; }

.pay-list { display: flex; flex-direction: column; gap: 10px; }
.pay {
  display: flex; align-items: center; gap: 12px;
  border: 1px solid var(--line-strong); background: #fff;
  border-radius: 10px; padding: 12px 14px; text-align: left;
}
.pay:hover { border-color: var(--brand); }
.pay.on { border-color: var(--brand); background: var(--brand-soft); }
.pay-icon {
  width: 36px; height: 36px; border-radius: 10px; flex: none;
  display: grid; place-items: center;
}
.pay-icon.balance { background: #fff2e8; color: var(--brand); }
.pay-icon.offline { background: var(--info-soft); color: var(--info); }
.pay-text { flex: 1; }
.pay-text strong { display: block; font-size: 14px; }
.pay-text small { color: var(--muted); font-size: 12px; }
.radio {
  width: 18px; height: 18px; border-radius: 50%; border: 2px solid var(--line-strong);
  position: relative; flex: none;
}
.radio.on { border-color: var(--brand); }
.radio.on::after {
  content: ''; position: absolute; inset: 3px; border-radius: 50%; background: var(--brand);
}

.side { position: sticky; top: 136px; }
.summary { display: flex; flex-direction: column; gap: 10px; }
.summary h3 { font-size: 15px; margin-bottom: 4px; }
.sum-row { display: flex; align-items: center; justify-content: space-between; font-size: 13px; color: var(--ink-2); }
.sum-row.total { padding-top: 12px; border-top: 1px dashed var(--line); font-size: 14px; }
.sum-tip {
  display: flex; gap: 6px; background: #fafbfc; border-radius: 8px;
  padding: 9px 10px; color: var(--muted); font-size: 11.5px; line-height: 1.6;
}
.sum-tip .app-icon { color: var(--ok); flex: none; margin-top: 1px; }
.summary .btn { margin-top: 4px; }

.check { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: var(--ink-2); }
.check input { accent-color: var(--brand); }

@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  .side { position: static; }
  .address-list { grid-template-columns: 1fr; }
}
@media (max-width: 560px) {
  .fields-grid { grid-template-columns: 1fr; }
  .line { flex-wrap: wrap; }
  .line-sub { width: auto; }
}
</style>
