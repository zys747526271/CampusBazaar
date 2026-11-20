<script setup>
import { computed } from 'vue'
import { money } from '@/utils/format'

const props = defineProps({
  data: { type: Array, default: () => [] }
})

const W = 640
const H = 190
const PAD_X = 18
const PAD_TOP = 16
const PAD_BOTTOM = 28

const points = computed(() => {
  const rows = props.data || []
  if (!rows.length) return { bars: [], line: '', labels: [], maxOrders: 0, maxAmount: 0 }
  const innerW = W - PAD_X * 2
  const innerH = H - PAD_TOP - PAD_BOTTOM
  const maxOrders = Math.max(...rows.map((r) => r.orders), 1)
  const maxAmount = Math.max(...rows.map((r) => r.amount), 1)
  const slot = innerW / rows.length
  const barW = Math.min(slot * 0.42, 36)

  const bars = rows.map((row, index) => {
    const h = (row.orders / maxOrders) * innerH
    return {
      x: PAD_X + slot * index + (slot - barW) / 2,
      y: H - PAD_BOTTOM - h,
      w: barW,
      h: Math.max(h, row.orders ? 3 : 0),
      label: row.orders,
      date: row.date
    }
  })

  const linePoints = rows.map((row, index) => {
    const x = PAD_X + slot * index + slot / 2
    const y = H - PAD_BOTTOM - (row.amount / maxAmount) * innerH
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })

  const labels = rows.map((row, index) => ({
    x: PAD_X + slot * index + slot / 2,
    text: row.date.slice(5)
  }))

  return { bars, line: linePoints.join(' '), labels, maxOrders, maxAmount }
})
</script>

<template>
  <div class="chart">
    <div class="legend">
      <span class="item"><i class="bar" /> 订单量</span>
      <span class="item"><i class="line" /> 成交额</span>
      <span class="scale">峰值订单 {{ points.maxOrders }} 笔 · 峰值成交 ¥{{ money(points.maxAmount) }}</span>
    </div>
    <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" class="svg" role="img" aria-label="近 7 天订单与成交额趋势">
      <line :x1="PAD_X" :x2="W - PAD_X" :y1="H - PAD_BOTTOM" :y2="H - PAD_BOTTOM" stroke="#eef0f4" />
      <rect
        v-for="(bar, index) in points.bars"
        :key="index"
        :x="bar.x"
        :y="bar.y"
        :width="bar.w"
        :height="bar.h"
        rx="4"
        fill="url(#barGradient)"
      >
        <title>{{ bar.date }}：{{ bar.label }} 笔</title>
      </rect>
      <polyline v-if="points.line" :points="points.line" fill="none" stroke="#2e6bff" stroke-width="2" stroke-linejoin="round" />
      <circle
        v-for="(point, index) in points.line.split(' ').filter(Boolean)"
        :key="`dot-${index}`"
        :cx="point.split(',')[0]"
        :cy="point.split(',')[1]"
        r="3"
        fill="#fff"
        stroke="#2e6bff"
        stroke-width="2"
      />
      <text v-for="(label, index) in points.labels" :key="`lb-${index}`" :x="label.x" :y="H - 8" text-anchor="middle" class="axis">
        {{ label.text }}
      </text>
      <defs>
        <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#ffb08a" />
          <stop offset="100%" stop-color="#ff7a45" />
        </linearGradient>
      </defs>
    </svg>
  </div>
</template>

<style scoped>
.chart { width: 100%; }
.legend { display: flex; align-items: center; gap: 16px; font-size: 12px; color: var(--muted); margin-bottom: 6px; flex-wrap: wrap; }
.item { display: inline-flex; align-items: center; gap: 6px; }
.bar { width: 10px; height: 10px; border-radius: 3px; background: linear-gradient(180deg, #ffb08a, #ff7a45); }
.line { width: 14px; height: 2px; background: #2e6bff; border-radius: 2px; }
.scale { margin-left: auto; }
.svg { width: 100%; height: 190px; display: block; }
.axis { font-size: 10px; fill: #a9b0ba; }
</style>
