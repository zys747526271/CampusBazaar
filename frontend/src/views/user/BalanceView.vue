<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { balanceApi } from '@/api'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppModal from '@/components/ui/AppModal.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { dateTime, money } from '@/utils/format'

const loading = ref(true)
const info = ref({ amount: 0, total_income: 0, recent_logs: [], recharge_enabled: false })
const logs = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const logLoading = ref(false)

const rechargeOpen = ref(false)
const rechargeBusy = ref(false)
const amount = ref('100')
const quickAmounts = [50, 100, 200, 500]

const toneOf = (type) => ({ 充值: 'ok', 支付: 'brand', 退款: 'info', 收入: 'ok' }[type] || '')

const loadInfo = async () => {
  try {
    info.value = await balanceApi.info()
  } catch (error) {
    toastError(error.message)
  }
}

const loadLogs = async (next = 1) => {
  logLoading.value = true
  try {
    const data = await balanceApi.logs({ page: next, per_page: 10 })
    logs.value = data.items || []
    total.value = data.total || 0
    pages.value = data.pages || 0
    page.value = data.page || 1
  } catch (error) {
    toastError(error.message)
  } finally {
    logLoading.value = false
  }
}

const recharge = async () => {
  const value = Number(amount.value)
  if (!value || value <= 0) {
    toastError('请输入正确的充值金额')
    return
  }
  rechargeBusy.value = true
  try {
    await balanceApi.recharge(value.toFixed(2))
    toastSuccess('充值成功（演示环境模拟到账）')
    rechargeOpen.value = false
    await Promise.all([loadInfo(), loadLogs(1)])
  } catch (error) {
    toastError(error.message)
  } finally {
    rechargeBusy.value = false
  }
}

const amountNumber = computed(() => Number(info.value.amount || 0))

onMounted(async () => {
  await loadInfo()
  await loadLogs(1)
  loading.value = false
})
</script>

<template>
  <div class="balance">
    <section class="wallet-card">
      <div class="wallet-info">
        <span class="wallet-label"><AppIcon name="wallet" :size="16" /> 账户余额</span>
        <strong class="wallet-amount">¥{{ money(amountNumber) }}</strong>
        <span class="wallet-tip">累计入账 ¥{{ money(info.total_income) }} · 余额支付即时到账</span>
      </div>
      <div class="wallet-actions">
        <button v-if="info.recharge_enabled" class="btn btn-dark" type="button" @click="rechargeOpen = true">
          充值
        </button>
        <RouterLink to="/products" class="btn">去消费</RouterLink>
      </div>
    </section>

    <section class="panel mt-16">
      <header class="head">
        <h2>收支明细</h2>
        <span class="text-sm text-muted">共 {{ total }} 条记录</span>
      </header>

      <div v-if="loading || logLoading" class="loading">
        <SkeletonBlock v-for="i in 4" :key="i" :h="44" radius="8px" />
      </div>

      <AppEmpty v-else-if="!logs.length" icon="wallet" title="还没有收支记录" description="完成一笔交易后这里会有记录" compact />

      <table v-else class="table">
        <thead>
          <tr>
            <th>类型</th>
            <th>说明</th>
            <th>金额</th>
            <th>余额</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id">
            <td><span class="tag" :class="toneOf(log.type) ? `tag-${toneOf(log.type)}` : ''">{{ log.type }}</span></td>
            <td>{{ log.remark || '—' }}</td>
            <td>
              <span :class="log.amount >= 0 ? 'text-ok' : 'text-danger'" class="amount">
                {{ log.amount >= 0 ? '+' : '-' }}{{ money(Math.abs(log.amount)) }}
              </span>
            </td>
            <td>¥{{ money(log.balance_after) }}</td>
            <td class="text-muted">{{ dateTime(log.created_at) }}</td>
          </tr>
        </tbody>
      </table>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="10" @change="loadLogs" />
    </section>

    <AppModal v-model="rechargeOpen" title="余额充值" width="420px">
      <div class="alert">
        <AppIcon name="info" :size="15" />
        当前为演示环境：充值不会产生真实扣款，仅用于体验余额支付流程。
      </div>
      <div class="field mt-16">
        <label>充值金额</label>
        <input v-model="amount" class="input" inputmode="decimal" placeholder="0.00" />
      </div>
      <div class="quick">
        <button v-for="value in quickAmounts" :key="value" type="button" class="btn btn-sm" @click="amount = String(value)">
          ¥{{ value }}
        </button>
      </div>
      <template #footer>
        <button class="btn" type="button" @click="rechargeOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="rechargeBusy" @click="recharge">
          {{ rechargeBusy ? '处理中…' : '确认充值' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.wallet-card {
  display: flex; align-items: center; justify-content: space-between; gap: 20px;
  padding: 26px 28px; border-radius: var(--radius-lg);
  background: linear-gradient(120deg, #1f2329, #353b45 55%, #4a3527);
  color: #fff;
}
.wallet-label { display: inline-flex; align-items: center; gap: 7px; font-size: 13px; opacity: .78; }
.wallet-amount { display: block; font-size: 40px; line-height: 1.2; letter-spacing: -.5px; font-variant-numeric: tabular-nums; }
.wallet-tip { font-size: 12px; opacity: .7; }
.wallet-actions { display: flex; gap: 10px; }
.wallet-actions .btn { background: rgba(255, 255, 255, .12); color: #fff; border-color: rgba(255, 255, 255, .2); }
.wallet-actions .btn:hover { background: rgba(255, 255, 255, .2); }
.wallet-actions .btn-dark { background: var(--brand); border-color: var(--brand); }
.wallet-actions .btn-dark:hover { background: var(--brand-dark); }

.head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.head h2 { font-size: 16px; }
.loading { display: flex; flex-direction: column; gap: 8px; }
.amount { font-variant-numeric: tabular-nums; font-weight: 600; }
.quick { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }

@media (max-width: 640px) {
  .wallet-card { flex-direction: column; align-items: flex-start; padding: 20px; }
  .wallet-amount { font-size: 32px; }
  .table th:nth-child(4), .table td:nth-child(4) { display: none; }
}
</style>
