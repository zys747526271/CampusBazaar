<script setup>
import ProductCard from './ProductCard.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'

defineProps({
  products: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  skeletonCount: { type: Number, default: 8 },
  showSeller: { type: Boolean, default: true },
  emptyTitle: { type: String, default: '没有找到相关商品' },
  emptyDescription: { type: String, default: '换个关键词或清空筛选条件试试' },
  columns: { type: Number, default: 0 }
})
const emit = defineEmits(['favorite'])

const gridStyle = (columns) => (columns ? { '--cols': columns } : {})
</script>

<template>
  <div class="grid" :style="gridStyle(columns)">
    <template v-if="loading">
      <div v-for="index in skeletonCount" :key="`sk-${index}`" class="sk-card">
        <SkeletonBlock :h="0" w="100%" radius="10px 10px 0 0" class="sk-cover" />
        <div class="sk-body">
          <SkeletonBlock :h="14" w="90%" />
          <SkeletonBlock :h="14" w="60%" />
          <SkeletonBlock :h="18" w="40%" />
        </div>
      </div>
    </template>
    <template v-else-if="products.length">
      <ProductCard
        v-for="item in products"
        :key="item.id"
        :product="item"
        :show-seller="showSeller"
        @favorite="emit('favorite', $event)"
      />
    </template>
    <div v-else class="empty-wrap">
      <AppEmpty icon="package" :title="emptyTitle" :description="emptyDescription">
        <slot name="empty-action" />
      </AppEmpty>
    </div>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(var(--cols, 5), minmax(0, 1fr));
  gap: 16px;
}
.sk-card { background: #fff; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.sk-cover { aspect-ratio: 1 / 1; height: auto !important; }
.sk-body { padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; }
.empty-wrap { grid-column: 1 / -1; background: #fff; border-radius: 12px; border: 1px solid var(--line); }

@media (max-width: 1200px) { .grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@media (max-width: 980px) { .grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 720px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; } }
</style>
