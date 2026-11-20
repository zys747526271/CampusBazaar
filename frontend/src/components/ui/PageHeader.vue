<script setup>
defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  back: { type: Boolean, default: false }
})
</script>

<template>
  <header class="page-header">
    <div class="text">
      <RouterLink v-if="back" to="/seller" class="back">
        <slot name="back">返回</slot>
      </RouterLink>
      <h1>{{ title }}</h1>
      <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 16px; flex-wrap: wrap; margin-bottom: 16px;
}
h1 { font-size: 22px; letter-spacing: -.3px; }
.subtitle { margin-top: 4px; color: var(--muted); font-size: 13px; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; }
.back { display: inline-flex; align-items: center; gap: 4px; color: var(--muted); font-size: 12.5px; margin-bottom: 4px; }
.back:hover { color: var(--brand); }
</style>
