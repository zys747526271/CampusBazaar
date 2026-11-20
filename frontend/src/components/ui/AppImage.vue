<script setup>
import { ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  src: { type: String, default: '' },
  alt: { type: String, default: '' },
  ratio: { type: String, default: '1 / 1' },
  radius: { type: String, default: '10px' },
  fit: { type: String, default: 'cover' }
})

const status = ref('loading')

watch(
  () => props.src,
  (value) => {
    status.value = value ? 'loading' : 'error'
  },
  { immediate: true }
)
</script>

<template>
  <div class="app-image" :style="{ aspectRatio: ratio, borderRadius: radius }">
    <div v-if="status === 'loading'" class="skeleton placeholder" />
    <div v-if="status === 'error'" class="placeholder fallback">
      <AppIcon name="image" :size="26" />
    </div>
    <img
      v-if="src && status !== 'error'"
      :src="src"
      :alt="alt"
      :style="{ objectFit: fit }"
      loading="lazy"
      decoding="async"
      @load="status = 'ok'"
      @error="status = 'error'"
    />
  </div>
</template>

<style scoped>
.app-image {
  position: relative;
  width: 100%;
  overflow: hidden;
  background: #f3f5f8;
}
.app-image img {
  width: 100%;
  height: 100%;
  display: block;
}
.placeholder {
  position: absolute;
  inset: 0;
}
.fallback {
  display: grid;
  place-items: center;
  color: #c2c8d2;
  background: linear-gradient(135deg, #f4f6f9, #e9edf2);
}
</style>
