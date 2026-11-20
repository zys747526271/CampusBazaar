<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  strokeWidth: { type: [Number, String], default: 1.8 },
  filled: { type: Boolean, default: false }
})

/** 图标全部用手写 SVG 路径，避免引入图标库增加包体积。 */
const ICONS = {
  search: ['M11 4a7 7 0 1 0 0 14a7 7 0 1 0 0-14', 'M16.2 16.2 21 21'],
  cart: ['M3 4h2l2.2 10.4a2 2 0 0 0 2 1.6h7.6a2 2 0 0 0 2-1.6L20.5 8H6',
    'M9 20.2a1 1 0 1 0 2 0a1 1 0 1 0-2 0', 'M16.5 20.2a1 1 0 1 0 2 0a1 1 0 1 0-2 0'],
  user: ['M12 4a4 4 0 1 0 0 8a4 4 0 1 0 0-8', 'M4 21c0-4 3.6-6 8-6s8 2 8 6'],
  heart: ['M12 20.5C9.5 18.6 3.5 14.2 3.5 9.6A4.6 4.6 0 0 1 12 6.6a4.6 4.6 0 0 1 8.5 3c0 4.6-6 9-8.5 10.9z'],
  bell: ['M18 16v-5a6 6 0 1 0-12 0v5l-2 3h16z', 'M10 22h4'],
  'chevron-down': ['M6 9l6 6 6-6'],
  'chevron-right': ['M9 6l6 6-6 6'],
  'chevron-left': ['M15 6l-6 6 6 6'],
  plus: ['M12 5v14', 'M5 12h14'],
  minus: ['M5 12h14'],
  check: ['M4 12.5l5 5L20 6.5'],
  close: ['M6 6l12 12', 'M18 6L6 18'],
  edit: ['M4 20h4l10-10-4-4L4 16z', 'M14 6l4 4'],
  trash: ['M4 7h16', 'M9 7V4h6v3', 'M6 7l1 13h10l1-13'],
  star: ['M12 3.6l2.7 5.4 6 .8-4.4 4.2 1.1 5.9-5.4-2.9-5.4 2.9 1.1-5.9L3.3 9.8l6-.8z'],
  package: ['M12 3l8 4.5v9L12 21l-8-4.5v-9z', 'M4 7.5l8 4.5 8-4.5', 'M12 12v9'],
  shop: ['M4 9h16v11H4z', 'M4 9l2-5h12l2 5', 'M9.5 20v-6h5v6'],
  chart: ['M4 20V11', 'M10 20V5', 'M16 20v-6', 'M22 20H2'],
  settings: ['M12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6', 'M12 2v3', 'M12 19v3', 'M2 12h3', 'M19 12h3',
    'M4.9 4.9l2.1 2.1', 'M17 17l2.1 2.1', 'M19.1 4.9L17 7', 'M7 17l-2.1 2.1'],
  logout: ['M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4', 'M16 8l4 4-4 4', 'M20 12H9'],
  'arrow-left': ['M19 12H5', 'M11 5l-7 7 7 7'],
  'arrow-right': ['M5 12h14', 'M13 5l7 7-7 7'],
  filter: ['M3 5h18', 'M6 12h12', 'M10 19h4'],
  upload: ['M12 16V4', 'M7 9l5-5 5 5', 'M4 20h16'],
  clock: ['M3 12a9 9 0 1 0 18 0a9 9 0 1 0-18 0', 'M12 7.5v5l3.2 2'],
  'map-pin': ['M12 21s7-5.4 7-11a7 7 0 1 0-14 0c0 5.6 7 11 7 11z', 'M12 7.5a2.5 2.5 0 1 0 0 5a2.5 2.5 0 1 0 0-5'],
  shield: ['M12 3l8 3v6c0 5-3.4 8-8 9-4.6-1-8-4-8-9V6z', 'M9 12l2 2 4-4'],
  alert: ['M3 12a9 9 0 1 0 18 0a9 9 0 1 0-18 0', 'M12 7.5v5.5', 'M12 16.4v.6'],
  refresh: ['M20 12a8 8 0 1 1-2.4-5.7', 'M20 4.5V10h-5.5'],
  eye: ['M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6S2 12 2 12z', 'M12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6'],
  tag: ['M4 4h7l9 9-7 7-9-9z', 'M8.4 7a1.2 1.2 0 1 0 0 2.4a1.2 1.2 0 1 0 0-2.4'],
  message: ['M21 12a8 8 0 0 1-8 8H8l-4 3v-5.4A8 8 0 0 1 12 4h1a8 8 0 0 1 8 8z'],
  grid: ['M4 4h6v6H4z', 'M14 4h6v6h-6z', 'M4 14h6v6H4z', 'M14 14h6v6h-6z'],
  list: ['M4 6h16', 'M4 12h16', 'M4 18h16'],
  camera: ['M4 8h3l2-2h6l2 2h3v11H4z', 'M12 10a3.2 3.2 0 1 0 0 6.4a3.2 3.2 0 1 0 0-6.4'],
  wallet: ['M3 7h18v12H3z', 'M3 7l2-3h12l2 3', 'M17 12.2a1.2 1.2 0 1 0 0 2.4a1.2 1.2 0 1 0 0-2.4'],
  truck: ['M3 7h11v9H3z', 'M14 10h4l3 3v3h-7z', 'M7 18.4a1.6 1.6 0 1 0 0-3.2a1.6 1.6 0 1 0 0 3.2',
    'M17 18.4a1.6 1.6 0 1 0 0-3.2a1.6 1.6 0 1 0 0 3.2'],
  'check-circle': ['M3 12a9 9 0 1 0 18 0a9 9 0 1 0-18 0', 'M8 12.5l2.6 2.6L16 9.5'],
  'x-circle': ['M3 12a9 9 0 1 0 18 0a9 9 0 1 0-18 0', 'M9 9l6 6', 'M15 9l-6 6'],
  info: ['M3 12a9 9 0 1 0 18 0a9 9 0 1 0-18 0', 'M12 11v5.5', 'M12 7.5v.6'],
  home: ['M4 11l8-7 8 7v9h-6v-6H10v6H4z'],
  layers: ['M12 3l9 5-9 5-9-5z', 'M3 13l9 5 9-5'],
  image: ['M4 5h16v14H4z', 'M4 16l4.5-4.5 4 4L16 12l4 4', 'M9 9.5a1.2 1.2 0 1 0 0 2.4a1.2 1.2 0 1 0 0-2.4'],
  'file-text': ['M6 3h8l4 4v14H6z', 'M14 3v4h4', 'M9 12h6', 'M9 16h6'],
  gift: ['M4 9h16v4H4z', 'M5 13h14v8H5z', 'M12 9v12', 'M12 9c-1-3-5-3.5-5-1s5 1 5 1', 'M12 9c1-3 5-3.5 5-1s-5 1-5 1'],
  'trend-up': ['M4 17l6-6 4 4 6-7', 'M15 8h5v5']
}

const paths = computed(() => ICONS[props.name] || ICONS.info)
const sizeValue = computed(() => (typeof props.size === 'number' ? `${props.size}` : props.size))
</script>

<template>
  <svg
    :width="sizeValue"
    :height="sizeValue"
    viewBox="0 0 24 24"
    :fill="filled ? 'currentColor' : 'none'"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    class="app-icon"
  >
    <path v-for="(d, index) in paths" :key="index" :d="d" />
  </svg>
</template>

<style scoped>
.app-icon { display: block; flex: none; }
</style>
