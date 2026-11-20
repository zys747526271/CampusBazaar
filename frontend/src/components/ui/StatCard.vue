<script setup>
import AppIcon from '@/components/ui/AppIcon.vue'

defineProps({
  label: { type: String, default: '' },
  value: { type: [String, Number], default: '' },
  hint: { type: String, default: '' },
  icon: { type: String, default: 'chart' },
  tone: { type: String, default: 'brand' }
})
</script>

<template>
  <div class="stat-card">
    <span class="icon" :class="`tone-${tone}`"><AppIcon :name="icon" :size="18" /></span>
    <div class="body">
      <p class="label">{{ label }}</p>
      <strong class="value">{{ value }}</strong>
      <p v-if="hint" class="hint">{{ hint }}</p>
    </div>
  </div>
</template>

<style scoped>
.stat-card {
  display: flex; gap: 12px; align-items: flex-start;
  background: #fff; border: 1px solid var(--line); border-radius: 12px;
  padding: 16px 18px; transition: all .16s;
}
.stat-card:hover { border-color: var(--line-strong); box-shadow: var(--shadow-xs); }
.icon {
  width: 38px; height: 38px; border-radius: 11px; flex: none;
  display: grid; place-items: center;
}
.tone-brand { background: var(--brand-soft); color: var(--brand); }
.tone-ok { background: var(--ok-soft); color: var(--ok); }
.tone-warn { background: var(--warn-soft); color: var(--warn); }
.tone-info { background: var(--info-soft); color: var(--info); }
.tone-danger { background: var(--danger-soft); color: var(--danger); }
.tone-muted { background: #f1f3f7; color: var(--ink-2); }

.label { font-size: 12px; color: var(--muted); }
.value { display: block; font-size: 24px; line-height: 1.3; letter-spacing: -.4px; font-variant-numeric: tabular-nums; }
.hint { font-size: 11.5px; color: var(--muted); margin-top: 2px; }
</style>
