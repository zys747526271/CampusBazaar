<script setup>
import AppIcon from './AppIcon.vue'

const props = defineProps({
  modelValue: { type: Number, default: 1 },
  min: { type: Number, default: 1 },
  max: { type: Number, default: 99 },
  size: { type: String, default: 'md' },
  disabled: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue', 'change'])

const update = (next) => {
  const value = Math.min(props.max, Math.max(props.min, Number(next) || props.min))
  if (value === props.modelValue) return
  emit('update:modelValue', value)
  emit('change', value)
}

const onInput = (event) => {
  const raw = event.target.value.replace(/[^\d]/g, '')
  event.target.value = raw
  if (raw) update(raw)
}
</script>

<template>
  <div class="stepper" :class="[`size-${size}`, { disabled }]">
    <button type="button" :disabled="disabled || modelValue <= min" @click="update(modelValue - 1)">
      <AppIcon name="minus" :size="14" />
    </button>
    <input
      :value="modelValue"
      :disabled="disabled"
      inputmode="numeric"
      aria-label="数量"
      @input="onInput"
      @blur="update($event.target.value)"
    />
    <button type="button" :disabled="disabled || modelValue >= max" @click="update(modelValue + 1)">
      <AppIcon name="plus" :size="14" />
    </button>
  </div>
</template>

<style scoped>
.stepper {
  display: inline-flex; align-items: center;
  border: 1px solid var(--line-strong); border-radius: 8px; overflow: hidden; background: #fff;
}
.stepper button {
  width: 32px; height: 34px; border: none; background: #fff; color: var(--ink-2);
  display: grid; place-items: center; transition: background .14s;
}
.stepper button:hover:not(:disabled) { background: var(--bg); color: var(--brand); }
.stepper button:disabled { color: #c9cfd8; cursor: not-allowed; }
.stepper input {
  width: 44px; height: 34px; border: none; border-inline: 1px solid var(--line);
  text-align: center; outline: none; font-size: 14px; font-variant-numeric: tabular-nums;
}
.size-sm button { width: 26px; height: 28px; }
.size-sm input { width: 36px; height: 28px; font-size: 13px; }
.disabled { opacity: .6; }
</style>
