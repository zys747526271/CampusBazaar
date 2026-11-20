<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  modelValue: { type: Number, default: 5 },
  count: { type: Number, default: 5 },
  size: { type: Number, default: 15 },
  showValue: { type: Boolean, default: false },
  interactive: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const stars = computed(() => Array.from({ length: props.count }, (_, i) => i + 1))

const setValue = (value) => {
  if (props.readonly || !props.interactive) return
  emit('update:modelValue', value)
}
</script>

<template>
  <div class="rating" :class="{ interactive: interactive && !readonly }">
    <button
      v-for="star in stars"
      :key="star"
      type="button"
      class="star"
      :class="{ on: star <= Math.round(modelValue), half: star - 0.5 === Number(modelValue) }"
      :disabled="readonly || !interactive"
      :aria-label="`${star} 星`"
      @click="setValue(star)"
    >
      <AppIcon name="star" :size="size" :filled="star <= Math.round(modelValue)" :stroke-width="1.4" />
    </button>
    <span v-if="showValue" class="value">{{ Number(modelValue || 0).toFixed(1) }}</span>
  </div>
</template>

<style scoped>
.rating { display: inline-flex; align-items: center; gap: 2px; }
.star {
  border: none; background: none; padding: 0; line-height: 0;
  color: #d8dde5; display: grid; place-items: center;
}
.star.on { color: #ff9f0a; }
.rating.interactive .star { cursor: pointer; transition: transform .12s; }
.rating.interactive .star:hover { transform: scale(1.12); }
.value { margin-left: 6px; font-size: 12.5px; color: var(--warn); font-weight: 600; }
</style>
