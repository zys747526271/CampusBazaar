<script setup>
import { onMounted, reactive, ref } from 'vue'
import { adminApiClient } from '@/api'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppModal from '@/components/ui/AppModal.vue'
import AppTabs from '@/components/ui/AppTabs.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { dateTime } from '@/utils/format'

const loading = ref(true)
const items = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const status = ref('待处理')

const modalOpen = ref(false)
const target = ref(null)
const busy = ref(false)
const form = reactive({ status: '已处理', result: '', action: 'none' })

const tabs = [
  { label: '待处理', value: '待处理' },
  { label: '已处理', value: '已处理' },
  { label: '已驳回', value: '已驳回' }
]

const actions = [
  { value: 'none', label: '仅记录处理结果' },
  { value: 'hide_comment', label: '隐藏被举报评价' },
  { value: 'off_product', label: '下架被举报商品' },
  { value: 'ban_user', label: '封禁被举报用户' }
]

const load = async (next = 1) => {
  loading.value = true
  try {
    const data = await adminApiClient.reports({ page: next, per_page: 10, status: status.value })
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
  load(1)
}

const openHandle = (report) => {
  target.value = report
  form.status = '已处理'
  form.result = ''
  form.action = 'none'
  modalOpen.value = true
}

const submit = async () => {
  if (form.status === '已处理' && !form.result.trim() && form.action === 'none') {
    toastError('请填写处理说明或选择处置动作')
    return
  }
  busy.value = true
  try {
    await adminApiClient.handleReport(target.value.id, {
      status: form.status,
      result: form.result.trim(),
      action: form.action
    })
    toastSuccess('举报已处理')
    modalOpen.value = false
    load(page.value)
  } catch (error) {
    toastError(error.message)
  } finally {
    busy.value = false
  }
}

onMounted(() => load(1))
</script>

<template>
  <div class="admin-reports">
    <header class="head">
      <div>
        <h1>举报处理</h1>
        <p class="text-sm text-muted">违规内容建议 24 小时内处置，处置动作会留痕</p>
      </div>
      <span class="tag tag-line">共 {{ total }} 条</span>
    </header>

    <div class="panel">
      <AppTabs :items="tabs" :model-value="status" @change="changeTab" />

      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 4" :key="i" :h="70" radius="10px" />
      </div>

      <AppEmpty
        v-else-if="!items.length"
        icon="shield"
        title="没有待处理的举报"
        description="平台秩序良好，继续保持"
        compact
      />

      <ul v-else class="list">
        <li v-for="report in items" :key="report.id" class="item">
          <div class="row">
            <span class="tag tag-danger">{{ report.reason }}</span>
            <span class="tag tag-line">{{ report.target_type_label }} #{{ report.target_id }}</span>
            <strong class="target">{{ report.target?.title || '对象已删除' }}</strong>
            <span class="text-xs text-muted time">{{ dateTime(report.created_at) }}</span>
          </div>
          <p v-if="report.detail" class="detail">{{ report.detail }}</p>
          <div class="foot">
            <span class="text-xs text-muted">举报人：{{ report.reporter?.nickname || '匿名' }}</span>
            <span v-if="report.handle_result" class="text-xs text-muted">处理结果：{{ report.handle_result }}</span>
            <button v-if="report.status === '待处理'" class="btn btn-sm btn-primary" type="button" @click="openHandle(report)">
              处理举报
            </button>
            <span v-else class="tag" :class="report.status === '已处理' ? 'tag-ok' : ''">{{ report.status }}</span>
          </div>
        </li>
      </ul>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="10" @change="load" />
    </div>

    <AppModal v-model="modalOpen" title="处理举报" width="480px">
      <div v-if="target" class="summary">
        <p><span>举报对象</span>{{ target.target_type_label }} #{{ target.target_id }} · {{ target.target?.title }}</p>
        <p><span>举报原因</span>{{ target.reason }}</p>
        <p v-if="target.detail"><span>补充说明</span>{{ target.detail }}</p>
      </div>

      <div class="field mt-12">
        <label>处置动作</label>
        <select v-model="form.action" class="select">
          <option v-for="action in actions" :key="action.value" :value="action.value">{{ action.label }}</option>
        </select>
      </div>
      <div class="field mt-12">
        <label>处理说明</label>
        <textarea v-model="form.result" class="textarea" maxlength="200" placeholder="例如：核实含联系方式引流，已隐藏该评价" />
      </div>
      <div class="field mt-12">
        <label>处理结论</label>
        <select v-model="form.status" class="select">
          <option value="已处理">已处理（举报成立）</option>
          <option value="已驳回">已驳回（举报不成立）</option>
        </select>
      </div>

      <template #footer>
        <button class="btn" type="button" @click="modalOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="busy" @click="submit">
          {{ busy ? '提交中…' : '确认处理' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.head h1 { font-size: 22px; }
.loading { display: flex; flex-direction: column; gap: 10px; padding-top: 10px; }

.list { display: flex; flex-direction: column; }
.item { padding: 14px 0; border-bottom: 1px solid var(--line); }
.item:last-child { border-bottom: none; }
.row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.target { font-size: 13.5px; }
.time { margin-left: auto; }
.detail { margin-top: 8px; color: var(--ink-2); font-size: 13px; background: #fafbfc; padding: 8px 10px; border-radius: 6px; }
.foot { display: flex; align-items: center; gap: 14px; margin-top: 10px; flex-wrap: wrap; }
.foot .btn { margin-left: auto; }

.summary { background: #fafbfc; border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 6px; font-size: 13px; }
.summary span { color: var(--muted); margin-right: 8px; }
</style>
