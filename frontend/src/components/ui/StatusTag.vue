<script setup>
import { computed } from 'vue'
import { ORDER_STATUS_TONE, PRODUCT_STATUS_TONE } from '@/utils/format'

const props = defineProps({
  status: { type: String, default: '' },
  kind: { type: String, default: 'order' }
})

const tone = computed(() => {
  const map = props.kind === 'product' ? PRODUCT_STATUS_TONE : ORDER_STATUS_TONE
  return map[props.status] || ''
})
</script>

<template>
  <span class="tag" :class="tone ? `tag-${tone}` : ''">{{ status }}</span>
</template>
