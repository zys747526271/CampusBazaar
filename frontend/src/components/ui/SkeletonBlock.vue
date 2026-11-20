<script setup>
defineProps({
  h: { type: [Number, String], default: 16 },
  w: { type: [Number, String], default: '100%' },
  radius: { type: String, default: '6px' },
  circle: { type: Boolean, default: false }
})
</script>

<template>
  <div
    class="skeleton"
    :style="{
      height: typeof h === 'number' ? `${h}px` : h,
      width: typeof w === 'number' ? `${w}px` : w,
      borderRadius: circle ? '50%' : radius
    }"
  />
</template>
