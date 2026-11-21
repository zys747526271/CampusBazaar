/** 展示层格式化：金额、时间、状态文案，统一在这里维护。 */

export const money = (value) => Number(value || 0).toFixed(2)

export const yuan = (value) => `¥${money(value)}`

export const maskPhone = (phone) => {
  if (!phone || phone.length < 7) return phone || ''
  return `${phone.slice(0, 3)}****${phone.slice(-4)}`
}

const pad = (n) => String(n).padStart(2, '0')

export const dateTime = (iso) => {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export const dateOnly = (iso) => {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export const relativeTime = (iso) => {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  if (Number.isNaN(diff)) return ''
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`
  if (diff < 7 * day) return `${Math.floor(diff / day)} 天前`
  return dateOnly(iso)
}

export const countdown = (iso) => {
  if (!iso) return ''
  const diff = new Date(iso).getTime() - Date.now()
  if (diff <= 0) return '已超时'
  const m = Math.floor(diff / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  return `${pad(m)}:${pad(s)}`
}

export const ORDER_STATUS = ['待付款', '已付款', '已发货', '已完成', '已取消', '退款中']

export const ORDER_STATUS_TONE = {
  待付款: 'warn',
  已付款: 'info',
  已发货: 'brand',
  已完成: 'ok',
  已取消: '',
  退款中: 'danger'
}

export const ORDER_ACTION_TEXT = {
  pay: '立即支付',
  confirm_offline: '等待卖家确认收款',
  cancel: '取消订单',
  confirm: '确认收货',
  refund: '申请退款',
  comment: '去评价',
  close: '关闭订单',
  ship: '发货',
  refund_approve: '同意退款',
  refund_reject: '驳回退款',
  admin_cancel: '取消订单',
  cancel_refund: '撤销退款申请',
  set_pickup_time: '确认自提时间'
}

export const PRODUCT_STATUS_TONE = {
  待审核: 'warn',
  已通过: 'ok',
  已下架: ''
}

export const CONDITION_LIST = ['全新', '几乎全新', '轻微使用', '明显使用']

//: 履约方式：v2.2 起「面交」并入「自提」
export const DELIVERY_LIST = ['自提', '快递']

//: 各履约方式可用的支付方式（服务端也会校验）
export const PAY_METHODS_BY_DELIVERY = {
  自提: ['余额', '线下'],
  快递: ['余额']
}

//: 地址数量超过该值时，结算页改用下拉选择，避免纵向过长
export const ADDRESS_DROPDOWN_THRESHOLD = 4

/** 商品卡片/详情用的履约标签 */
export const deliveryLabels = (product) => {
  if (!product) return []
  if (Array.isArray(product.delivery_labels) && product.delivery_labels.length) return product.delivery_labels
  const labels = []
  if (product.supports_pickup) labels.push('自提')
  if (product.supports_express) labels.push(product.free_shipping ? '包邮' : '快递')
  return labels
}

export const shippingText = (product) => {
  if (!product || !product.supports_express) return ''
  if (product.free_shipping) return '包邮'
  return `运费 ¥${money(product.shipping_fee)}`
}

export const REPORT_REASONS = ['虚假信息', '违禁物品', '价格欺诈', '辱骂骚扰', '联系方式引流', '其他']

/** 把后端字段级错误转成 {字段: 文案} */
export const pickFieldErrors = (error) => (error && typeof error.details === 'object' ? error.details : {})

export const displayError = (error) => (error?.message ? String(error.message) : '操作失败，请稍后重试')
