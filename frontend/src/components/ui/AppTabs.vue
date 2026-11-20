<script setup>
defineProps({
  items: { type: Array, default: () => [] },
  modelValue: { type: [String, Number], default: '' },
  variant: { type: String, default: 'line' },
  grow: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue', 'change'])

const select = (value) => {
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<template>
  <div class="tabs" :class="[`tabs-${variant}`, { grow }]" role="tablist">
    <button
      v-for="item in items"
      :key="item.value"
      type="button"
      role="tab"
      class="tab"
      :class="{ active: modelValue === item.value }"
      :aria-selected="modelValue === item.value"
      @click="select(item.value)"
    >
      <span>{{ item.label }}</span>
      <span v-if="item.badge" class="count">{{ item.badge }}</span>
    </button>
  </div>
</template>

<style scoped>
.tabs { display: flex; align-items: center; gap: 4px; overflow-x: auto; scrollbar-width: none; }
.tabs::-webkit-scrollbar { display: none; }
.tabs.grow .tab { flex: 1; justify-content: center; }

.tabs-line { border-bottom: 1px solid var(--line); gap: 24px; }
.tabs-line .tab {
  position: relative; border: none; background: none; padding: 12px 0;
  color: var(--ink-2); font-size: 14.5px; white-space: nowrap;
}
.tabs-line .tab::after {
  content: ''; position: absolute; left: 0; right: 0; bottom: -1px; height: 2px;
  background: var(--brand); border-radius: 2px; transform: scaleX(0); transition: transform .18s;
}
.tabs-line .tab.active { color: var(--brand); font-weight: 600; }
.tabs-line .tab.active::after { transform: scaleX(1); }

.tabs-pill {
  background: #f2f4f7; padding: 3px; border-radius: 10px; display: inline-flex;
}
.tabs-pill .tab {
  border: none; background: none; color: var(--ink-2);
  padding: 6px 14px; border-radius: 8px; font-size: 13.5px; white-space: nowrap;
}
.tabs-pill .tab.active { background: #fff; color: var(--ink); font-weight: 600; box-shadow: var(--shadow-xs); }

.count {
  display: inline-grid; place-items: center; min-width: 18px; height: 18px;
  margin-left: 6px; padding: 0 5px; border-radius: 999px;
  background: var(--brand-soft); color: var(--brand); font-size: 11px; font-weight: 600;
}
.tabs-pill .tab.active .count { background: var(--brand); color: #fff; }
</style>
