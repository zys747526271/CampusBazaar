<script setup>
import { onMounted, ref } from 'vue'
import { adminApiClient } from '@/api'
import { toastError } from '@/composables/useToast'
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
const keyword = ref('')

const toneOf = (action) => {
  if (action.includes('封禁') || action.includes('下架') || action.includes('隐藏') || action.includes('删除')) return 'tag-danger'
  if (action.includes('通过') || action.includes('恢复') || action.includes('解封')) return 'tag-ok'
  if (action.includes('退款') || action.includes('重置')) return 'tag-warn'
  return 'tag-info'
}

const load = async (next = 1) => {
  loading.value = true
  try {
    const data = await adminApiClient.auditLogs({ page: next, per_page: 20, keyword: keyword.value || undefined })
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

onMounted(() => load(1))
</script>

<template>
  <div class="admin-audit">
    <header class="head">
      <div>
        <h1>操作审计</h1>
        <p class="text-sm text-muted">共 {{ total }} 条记录 · 审核、下架、封禁、隐藏评价全部留痕</p>
      </div>
      <form class="search" @submit.prevent="load(1)">
        <AppIcon name="search" :size="15" />
        <input v-model="keyword" placeholder="搜索操作或管理员" maxlength="30" />
        <button class="btn btn-sm" type="submit">搜索</button>
      </form>
    </header>

    <div class="panel">
      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 8" :key="i" :h="38" radius="6px" />
      </div>

      <AppEmpty v-else-if="!items.length" icon="shield" title="暂无审计记录" description="管理员执行治理操作后会出现在这里" compact />

      <table v-else class="table">
        <thead>
          <tr><th>时间</th><th>管理员</th><th>操作</th><th>对象</th><th>说明</th><th>IP</th></tr>
        </thead>
        <tbody>
          <tr v-for="log in items" :key="log.id">
            <td class="text-muted time">{{ dateTime(log.created_at) }}</td>
            <td>{{ log.admin_name }}</td>
            <td><span class="tag" :class="toneOf(log.action)">{{ log.action }}</span></td>
            <td class="mono">{{ log.target_type || '—' }}{{ log.target_id ? `#${log.target_id}` : '' }}</td>
            <td class="detail">{{ log.detail || '—' }}</td>
            <td class="mono text-muted">{{ log.ip }}</td>
          </tr>
        </tbody>
      </table>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="20" @change="load" />
    </div>
  </div>
</template>

<style scoped>
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.head h1 { font-size: 22px; }
.search { display: flex; align-items: center; gap: 6px; border: 1px solid var(--line-strong); border-radius: 8px; padding: 3px 4px 3px 10px; background: #fff; color: var(--muted); }
.search input { border: none; outline: none; height: 28px; width: 170px; font-size: 13px; }
.loading { display: flex; flex-direction: column; gap: 8px; }
.mono { font-family: var(--mono); font-size: 12px; }
.time { white-space: nowrap; font-size: 12px; }
.detail { max-width: 280px; }
</style>
