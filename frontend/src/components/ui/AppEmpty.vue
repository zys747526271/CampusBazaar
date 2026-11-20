<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  icon: { type: String, default: 'package' },
  title: { type: String, default: '这里还什么都没有' },
  description: { type: String, default: '' },
  compact: { type: Boolean, default: false }
})
</script>

<template>
  <div class="empty" :class="{ compact }">
    <div class="empty-icon">
      <AppIcon :name="icon" :size="compact ? 24 : 30" />
    </div>
    <div>
      <p class="empty-title">{{ title }}</p>
      <p v-if="description" class="text-sm text-muted mt-8">{{ description }}</p>
    </div>
    <slot />
  </div>
</template>

<style scoped>
.empty.compact { padding: 32px 16px; gap: 10px; }
.empty.compact .empty-icon { width: 56px; height: 56px; border-radius: 18px; }
</style>
