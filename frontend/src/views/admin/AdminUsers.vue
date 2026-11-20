<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminApiClient, saveBlob } from '@/api'
import { confirmAction } from '@/composables/useConfirm'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppModal from '@/components/ui/AppModal.vue'
import AppImage from '@/components/ui/AppImage.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { dateOnly, dateTime, money } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const keyword = ref(route.query.keyword || '')
const status = ref(route.query.status || '')
const items = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)

const detailOpen = ref(false)
const detail = ref(null)
const detailLoading = ref(false)

const banOpen = ref(false)
const banTarget = ref(null)
const banForm = reactive({ banned: true, reason: '' })
const banBusy = ref(false)

const statusOptions = [
  { value: '', label: '全部用户' },
  { value: 'buyer', label: '仅买家' },
  { value: 'seller', label: '卖家' },
  { value: 'banned', label: '已封禁' }
]

const exportCsv = async () => {
  try {
    const res = await adminApiClient.exportCsv('users')
    saveBlob(res.data, `campus-users-${new Date().toISOString().slice(0, 10)}.csv`)
    toastSuccess('已导出 CSV')
  } catch (error) {
    toastError(error.message)
  }
}

const load = async (next = 1) => {
  loading.value = true
  try {
    const data = await adminApiClient.users({
      page: next,
      per_page: 15,
      keyword: keyword.value || undefined,
      status: status.value || undefined
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
  router.replace({ path: '/admin/users', query: { ...(keyword.value ? { keyword: keyword.value } : {}), ...(status.value ? { status: status.value } : {}) } })
  load(1)
}

const openDetail = async (user) => {
  detailOpen.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await adminApiClient.user(user.id)
  } catch (error) {
    toastError(error.message)
    detailOpen.value = false
  } finally {
    detailLoading.value = false
  }
}

const openBan = (user) => {
  banTarget.value = user
  banForm.banned = !user.is_banned
  banForm.reason = ''
  banOpen.value = true
}

const submitBan = async () => {
  if (banForm.banned && !banForm.reason.trim()) {
    toastError('请填写封禁原因')
    return
  }
  banBusy.value = true
  try {
    await adminApiClient.banUser(banTarget.value.id, { banned: banForm.banned, reason: banForm.reason.trim() })
    toastSuccess(banForm.banned ? '已封禁并下架其商品' : '已解封')
    banOpen.value = false
    load(page.value)
  } catch (error) {
    toastError(error.message)
  } finally {
    banBusy.value = false
  }
}

const resetPassword = async (user) => {
  const ok = await confirmAction({
    title: '重置密码',
    message: `将为「${user.nickname}」生成一个临时密码，用户需使用新密码登录。`,
    confirmText: '重置密码',
    danger: false
  })
  if (!ok) return
  try {
    const data = await adminApiClient.resetUserPassword(user.id)
    toastSuccess(`临时密码：${data.new_password}（请复制后告知用户）`)
  } catch (error) {
    toastError(error.message)
  }
}

const currentStatusLabel = computed(() => statusOptions.find((item) => item.value === status.value)?.label || '全部用户')

onMounted(() => load(1))
</script>

<template>
  <div class="admin-users">
    <header class="head">
      <div>
        <h1>用户管理</h1>
        <p class="text-sm text-muted">共 {{ total }} 位用户 · {{ currentStatusLabel }}</p>
      </div>
      <div class="toolbar">
        <form class="search" @submit.prevent="search">
          <AppIcon name="search" :size="15" />
          <input v-model="keyword" placeholder="搜索昵称 / 手机号" maxlength="30" />
        </form>
        <select v-model="status" class="select input-sm" @change="search">
          <option v-for="option in statusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
        <button class="btn btn-sm" type="button" @click="load(page)">刷新</button>
        <button class="btn btn-sm" type="button" @click="exportCsv">导出 CSV</button>
      </div>
    </header>

    <div class="panel">
      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 6" :key="i" :h="46" radius="8px" />
      </div>

      <AppEmpty v-else-if="!items.length" icon="user" title="没有匹配的用户" description="换个关键词或筛选条件试试" compact />

      <table v-else class="table">
        <thead>
          <tr>
            <th>用户</th>
            <th>手机号</th>
            <th>身份</th>
            <th>订单 / 消费</th>
            <th>状态</th>
            <th>注册时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in items" :key="user.id">
            <td>
              <div class="user-cell">
                <span class="avatar">
                  <img v-if="user.avatar_url" :src="user.avatar_url" alt="" />
                  <template v-else>{{ (user.nickname || '用').slice(0, 1) }}</template>
                </span>
                <div>
                  <p class="name">{{ user.nickname }}</p>
                  <p class="text-xs text-muted">ID {{ user.id }} · {{ user.campus || '未填写校区' }}</p>
                </div>
              </div>
            </td>
            <td class="mono">{{ user.phone }}</td>
            <td>
              <span class="tag" :class="user.is_seller ? 'tag-brand' : 'tag-line'">{{ user.is_seller ? '卖家' : '买家' }}</span>
            </td>
            <td>{{ user.order_count || 0 }} 单 / ¥{{ money(user.spent || 0) }}</td>
            <td>
              <span class="tag" :class="user.is_banned ? 'tag-danger' : 'tag-ok'">{{ user.is_banned ? '已封禁' : '正常' }}</span>
            </td>
            <td class="text-muted">{{ dateOnly(user.created_at) }}</td>
            <td>
              <div class="table-actions">
                <button class="btn btn-sm" type="button" @click="openDetail(user)">详情</button>
                <button class="btn btn-sm" :class="{ 'btn-danger': !user.is_banned }" type="button" @click="openBan(user)">
                  {{ user.is_banned ? '解封' : '封禁' }}
                </button>
                <button class="btn btn-sm" type="button" @click="resetPassword(user)">重置密码</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="15" @change="load" />
    </div>

    <AppModal v-model="detailOpen" title="用户详情" width="640px">
      <div v-if="detailLoading" class="loading">
        <SkeletonBlock :h="60" radius="8px" />
        <SkeletonBlock :h="120" radius="8px" />
      </div>
      <template v-else-if="detail">
        <div class="detail-head">
          <span class="avatar big">
            <img v-if="detail.avatar_url" :src="detail.avatar_url" alt="" />
            <template v-else>{{ (detail.nickname || '用').slice(0, 1) }}</template>
          </span>
          <div>
            <h3>{{ detail.nickname }}</h3>
            <p class="text-xs text-muted">{{ detail.phone }} · {{ detail.campus || '未填写校区' }}</p>
          </div>
          <span class="tag" :class="detail.is_banned ? 'tag-danger' : 'tag-ok'">{{ detail.is_banned ? '已封禁' : '正常' }}</span>
        </div>

        <div class="detail-grid">
          <div><span>注册时间</span><p>{{ dateTime(detail.created_at) }}</p></div>
          <div><span>最近登录</span><p>{{ dateTime(detail.last_login_at) }}</p></div>
          <div><span>订单数</span><p>{{ detail.order_count || 0 }}</p></div>
          <div><span>累计消费</span><p>¥{{ money(detail.spent || 0) }}</p></div>
          <div><span>发布商品</span><p>{{ detail.products?.total || 0 }} 件（在售 {{ detail.products?.on_sale || 0 }}）</p></div>
          <div><span>封禁原因</span><p>{{ detail.ban_reason || '—' }}</p></div>
        </div>

        <h4 class="section-label">最近订单</h4>
        <AppEmpty v-if="!detail.recent_orders?.length" icon="file-text" title="暂无订单" compact />
        <table v-else class="table">
          <thead><tr><th>订单号</th><th>金额</th><th>状态</th><th>时间</th></tr></thead>
          <tbody>
            <tr v-for="order in detail.recent_orders" :key="order.id">
              <td class="mono">{{ order.order_no }}</td>
              <td>¥{{ money(order.total_amount) }}</td>
              <td>{{ order.status }}</td>
              <td class="text-muted">{{ dateOnly(order.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </template>
      <template #footer>
        <button class="btn" type="button" @click="detailOpen = false">关闭</button>
      </template>
    </AppModal>

    <AppModal v-model="banOpen" :title="banForm.banned ? '封禁用户' : '解封用户'" width="420px">
      <div v-if="banTarget" class="alert" :class="banForm.banned ? 'alert-danger' : 'alert-ok'">
        <AppIcon :name="banForm.banned ? 'alert' : 'info'" :size="15" />
        <span v-if="banForm.banned">封禁后该用户无法登录、无法下单，已发布商品会自动下架。</span>
        <span v-else>解封后该用户可以正常登录与交易。</span>
      </div>
      <p class="mt-12 text-sm">用户：<strong>{{ banTarget?.nickname }}</strong>（{{ banTarget?.phone }}）</p>
      <div v-if="banForm.banned" class="field mt-12">
        <label>封禁原因</label>
        <textarea v-model="banForm.reason" class="textarea" maxlength="100" placeholder="例如：多次发布违规商品、骚扰其他用户" />
      </div>
      <template #footer>
        <button class="btn" type="button" @click="banOpen = false">取消</button>
        <button class="btn" :class="banForm.banned ? 'btn-danger' : 'btn-primary'" type="button" :disabled="banBusy" @click="submitBan">
          {{ banBusy ? '处理中…' : banForm.banned ? '确认封禁' : '确认解封' }}
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
.search input { border: none; outline: none; height: 28px; width: 180px; font-size: 13px; }
.loading { display: flex; flex-direction: column; gap: 8px; }
.mono { font-family: var(--mono); font-size: 12px; color: var(--ink-2); }

.user-cell { display: flex; align-items: center; gap: 10px; }
.avatar {
  width: 34px; height: 34px; border-radius: 50%; flex: none;
  display: grid; place-items: center; font-size: 12px; font-weight: 700;
  background: #eef1f6; color: var(--ink-2); overflow: hidden;
}
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.avatar.big { width: 48px; height: 48px; font-size: 16px; }
.name { font-size: 13.5px; }

.detail-head { display: flex; align-items: center; gap: 12px; padding-bottom: 14px; border-bottom: 1px solid var(--line); }
.detail-head h3 { font-size: 16px; }
.detail-head .tag { margin-left: auto; }
.detail-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 14px; }
.detail-grid span { color: var(--muted); font-size: 11.5px; }
.detail-grid p { font-size: 13px; margin-top: 2px; }
.section-label { font-size: 13px; color: var(--muted); margin: 18px 0 8px; }
</style>
