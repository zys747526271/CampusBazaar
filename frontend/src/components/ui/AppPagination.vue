<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  page: { type: Number, default: 1 },
  pages: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  perPage: { type: Number, default: 20 }
})
const emit = defineEmits(['change'])

const windowPages = computed(() => {
  const current = props.page
  const last = props.pages
  if (last <= 7) return Array.from({ length: last }, (_, i) => i + 1)
  const result = [1]
  const start = Math.max(2, current - 1)
  const end = Math.min(last - 1, current + 1)
  if (start > 2) result.push('…')
  for (let i = start; i <= end; i += 1) result.push(i)
  if (end < last - 1) result.push('…')
  result.push(last)
  return result
})

const go = (target) => {
  if (target === '…' || target === props.page) return
  if (target < 1 || target > props.pages) return
  emit('change', target)
}
</script>

<template>
  <div v-if="pages > 1 || total > 0" class="pagination">
    <span class="summary">共 {{ total }} 条</span>
    <button class="page-btn" :disabled="page <= 1" @click="go(page - 1)">
      <AppIcon name="chevron-left" :size="15" />
    </button>
    <button
      v-for="(item, index) in windowPages"
      :key="`${item}-${index}`"
      class="page-btn"
      :class="{ active: item === page, dots: item === '…' }"
      :disabled="item === '…'"
      @click="go(item)"
    >
      {{ item }}
    </button>
    <button class="page-btn" :disabled="page >= pages" @click="go(page + 1)">
      <AppIcon name="chevron-right" :size="15" />
    </button>
  </div>
</template>

<style scoped>
.pagination { display: flex; align-items: center; gap: 6px; justify-content: flex-end; padding: 18px 0 4px; }
.summary { color: var(--muted); font-size: 12.5px; margin-right: 8px; }
.page-btn {
  min-width: 32px; height: 32px; padding: 0 8px;
  display: inline-grid; place-items: center;
  border: 1px solid var(--line-strong); background: #fff;
  border-radius: 8px; color: var(--ink-2); font-size: 13px;
  transition: all .16s;
}
.page-btn:hover:not(:disabled) { border-color: var(--brand); color: var(--brand); }
.page-btn.active { background: var(--brand); border-color: var(--brand); color: #fff; font-weight: 600; }
.page-btn.dots { border: none; background: none; cursor: default; color: var(--muted); }
.page-btn:disabled { opacity: .45; cursor: not-allowed; }
@media (max-width: 720px) {
  .pagination { justify-content: center; flex-wrap: wrap; }
  .summary { width: 100%; text-align: center; margin: 0 0 4px; }
}
</style>
