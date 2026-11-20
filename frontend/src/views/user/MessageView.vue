<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { messageApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { toastError, toastSuccess } from '@/composables/useToast'
import AppTabs from '@/components/ui/AppTabs.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { dateTime } from '@/utils/format'

const router = useRouter()
const app = useAppStore()

const loading = ref(true)
const items = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const tab = ref('all')

const tabs = [
  { label: '全部消息', value: 'all' },
  { label: '未读', value: 'unread' }
]

const toneOf = (type) => ({ 订单: 'brand', 资金: 'ok', 审核: 'warn', 系统: 'info' }[type] || '')

const load = async (next = 1) => {
  loading.value = true
  try {
    const params = { page: next, per_page: 10 }
    if (tab.value === 'unread') params.unread = 1
    const data = await messageApi.list(params)
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
  tab.value = value
  load(1)
}

const openMessage = async (message) => {
  if (!message.is_read) {
    try {
      await messageApi.read(message.id)
      message.is_read = true
      app.loadUnread()
    } catch (error) {
      /* 忽略 */
    }
  }
  if (message.link) router.push(message.link)
}

const readAll = async () => {
  try {
    await messageApi.readAll()
    toastSuccess('已全部标记为已读')
    app.loadUnread()
    load(page.value)
  } catch (error) {
    toastError(error.message)
  }
}

const unreadCount = computed(() => items.value.filter((item) => !item.is_read).length)

onMounted(() => load(1))
</script>

<template>
  <div class="messages">
    <div class="panel">
      <header class="head">
        <div>
          <h1>我的消息</h1>
          <p class="text-sm text-muted">订单、审核、资金变动都会在这里通知你</p>
        </div>
        <button class="btn btn-sm" type="button" @click="readAll">全部已读</button>
      </header>

      <AppTabs :items="tabs" :model-value="tab" @change="changeTab" />

      <div v-if="loading" class="loading">
        <SkeletonBlock v-for="i in 4" :key="i" :h="64" radius="10px" />
      </div>

      <AppEmpty
        v-else-if="!items.length"
        icon="bell"
        :title="tab === 'unread' ? '没有未读消息' : '暂时没有消息'"
        description="有新的订单或审核结果时，我们会在这里通知你"
        compact
      />

      <ul v-else class="list">
        <li v-for="message in items" :key="message.id" class="item" :class="{ unread: !message.is_read }">
          <button class="item-btn" type="button" @click="openMessage(message)">
            <span class="dot-wrap"><i v-if="!message.is_read" class="dot" /></span>
            <div class="item-body">
              <div class="item-top">
                <span class="tag" :class="toneOf(message.type) ? `tag-${toneOf(message.type)}` : ''">{{ message.type }}</span>
                <strong>{{ message.title }}</strong>
                <span class="time">{{ dateTime(message.created_at) }}</span>
              </div>
              <p class="content">{{ message.content }}</p>
            </div>
            <AppIcon name="chevron-right" :size="16" class="arrow" />
          </button>
        </li>
      </ul>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="10" @change="load" />
    </div>
  </div>
</template>

<style scoped>
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.head h1 { font-size: 21px; letter-spacing: -.3px; }
.loading { display: flex; flex-direction: column; gap: 10px; padding-top: 12px; }

.list { display: flex; flex-direction: column; }
.item { border-bottom: 1px solid var(--line); }
.item:last-child { border-bottom: none; }
.item-btn { display: flex; align-items: flex-start; gap: 10px; width: 100%; border: none; background: none; padding: 14px 4px; text-align: left; }
.item.unread { background: #fffaf7; }
.item-btn:hover { background: var(--hover); }

.dot-wrap { width: 10px; padding-top: 7px; flex: none; }
.dot { display: block; width: 6px; height: 6px; border-radius: 50%; background: var(--brand); }

.item-body { flex: 1; min-width: 0; }
.item-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.item-top strong { font-size: 14px; }
.time { margin-left: auto; color: var(--muted); font-size: 11.5px; }
.content { margin-top: 4px; color: var(--muted); font-size: 13px; line-height: 1.7; }
.arrow { color: var(--muted-2); margin-top: 4px; }
</style>
