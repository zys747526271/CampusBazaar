<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalogApi } from '@/api'
import { useAppStore } from '@/stores/app'
import ProductGrid from '@/components/product/ProductGrid.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { CONDITION_LIST } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const app = useAppStore()

const loading = ref(true)
const items = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const showFilter = ref(false)

const minInput = ref('')
const maxInput = ref('')

const tags = computed(() => app.tags)
const query = computed(() => route.query)

const activeTag = computed(() => Number(route.query.tag_id) || 0)
const activeCondition = computed(() => route.query.condition || '')
const activeSort = computed(() => route.query.sort || 'created_at')
const keyword = computed(() => route.query.keyword || '')
const hasFilter = computed(
  () => Boolean(route.query.tag_id || route.query.keyword || route.query.min_price || route.query.max_price || route.query.condition)
)

const sortOptions = [
  { value: 'created_at', label: '最新发布' },
  { value: 'sales', label: '销量优先' },
  { value: 'views', label: '浏览最多' }
]

const priceRanges = [
  { label: '0-20', min: 0, max: 20 },
  { label: '20-50', min: 20, max: 50 },
  { label: '50-200', min: 50, max: 200 },
  { label: '200-500', min: 200, max: 500 },
  { label: '500 以上', min: 500, max: '' }
]

const activePriceLabel = computed(() => {
  const min = route.query.min_price
  const max = route.query.max_price
  if (min === undefined && max === undefined) return ''
  return `¥${min || 0} - ${max || '不限'}`
})

const fetchList = async () => {
  loading.value = true
  try {
    const params = { ...route.query, per_page: 20, page: route.query.page || 1 }
    const data = await catalogApi.products(params)
    items.value = data.items || []
    total.value = data.total || 0
    pages.value = data.pages || 0
    page.value = data.page || 1
  } catch (error) {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const updateQuery = (patch, resetPage = true) => {
  const next = { ...route.query, ...patch }
  if (resetPage) delete next.page
  Object.keys(next).forEach((key) => {
    if (next[key] === '' || next[key] === null || next[key] === undefined) delete next[key]
  })
  router.push({ path: '/products', query: next })
}

const selectTag = (id) => updateQuery({ tag_id: id || undefined })
const setSort = (value) => updateQuery({ sort: value })
const toggleSortOrder = () => updateQuery({ order: route.query.order === 'asc' ? 'desc' : 'asc' })
const selectCondition = (value) => updateQuery({ condition: activeCondition.value === value ? undefined : value })
const selectPrice = (range) => updateQuery({ min_price: range.min, max_price: range.max })
const applyPrice = () => {
  updateQuery({ min_price: minInput.value || undefined, max_price: maxInput.value || undefined })
  showFilter.value = false
}
const resetFilters = () => router.push({ path: '/products' })
const goPage = (next) => {
  updateQuery({ page: next }, false)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const initPriceInputs = () => {
  minInput.value = route.query.min_price ?? ''
  maxInput.value = route.query.max_price ?? ''
}

watch(
  () => route.query,
  () => {
    fetchList()
    initPriceInputs()
  }
)

onMounted(async () => {
  await app.loadFilters()
  initPriceInputs()
  fetchList()
})
</script>

<template>
  <div class="container list-page">
    <nav class="crumb">
      <RouterLink to="/">首页</RouterLink>
      <AppIcon name="chevron-right" :size="12" />
      <span>全部商品</span>
      <template v-if="keyword">
        <AppIcon name="chevron-right" :size="12" />
        <span class="text-brand">“{{ keyword }}” 的搜索结果</span>
      </template>
    </nav>

    <div class="layout">
      <aside class="filters" :class="{ open: showFilter }">
        <div class="filter-head">
          <strong>筛选</strong>
          <button v-if="hasFilter" class="btn-text" type="button" @click="resetFilters">清空</button>
          <button class="close-mobile" type="button" aria-label="关闭" @click="showFilter = false">
            <AppIcon name="close" :size="16" />
          </button>
        </div>

        <div class="filter-block">
          <h4>商品分类</h4>
          <button class="option" :class="{ on: !activeTag }" type="button" @click="selectTag(0)">
            全部 <span class="count">全站</span>
          </button>
          <button
            v-for="tag in tags"
            :key="tag.id"
            class="option"
            :class="{ on: activeTag === tag.id }"
            type="button"
            @click="selectTag(tag.id)"
          >
            {{ tag.name }} <span class="count">{{ tag.product_count || 0 }}</span>
          </button>
        </div>

        <div class="filter-block">
          <h4>价格区间</h4>
          <div class="price-chips">
            <button
              v-for="range in priceRanges"
              :key="range.label"
              type="button"
              class="chip"
              :class="{ on: activePriceLabel === `¥${range.min} - ${range.max || '不限'}` }"
              @click="selectPrice(range)"
            >
              {{ range.label }}
            </button>
          </div>
          <div class="price-inputs">
            <input v-model="minInput" class="input input-sm" placeholder="最低" inputmode="numeric" />
            <span>-</span>
            <input v-model="maxInput" class="input input-sm" placeholder="最高" inputmode="numeric" />
          </div>
          <button class="btn btn-sm btn-block mt-8" type="button" @click="applyPrice">确定</button>
        </div>

        <div class="filter-block">
          <h4>成色</h4>
          <div class="chip-wrap">
            <button
              v-for="item in CONDITION_LIST"
              :key="item"
              type="button"
              class="chip"
              :class="{ on: activeCondition === item }"
              @click="selectCondition(item)"
            >
              {{ item }}
            </button>
          </div>
        </div>
      </aside>

      <section class="results">
        <div class="toolbar">
          <div class="sorts">
            <button
              v-for="option in sortOptions"
              :key="option.value"
              type="button"
              class="sort"
              :class="{ on: activeSort === option.value }"
              @click="setSort(option.value)"
            >
              {{ option.label }}
            </button>
            <button type="button" class="sort" :class="{ on: activeSort === 'price' }" @click="setSort('price')">
              价格
              <span class="order" :class="{ asc: route.query.order === 'asc' }">
                <AppIcon name="chevron-down" :size="12" />
              </span>
            </button>
            <button
              v-if="activeSort === 'price'"
              class="btn-text order-toggle"
              type="button"
              @click="toggleSortOrder"
            >
              {{ route.query.order === 'asc' ? '从低到高' : '从高到低' }}
            </button>
          </div>
          <div class="toolbar-right">
            <span class="text-sm text-muted">共 {{ total }} 件</span>
            <button class="filter-toggle" type="button" @click="showFilter = true">
              <AppIcon name="filter" :size="15" /> 筛选
            </button>
          </div>
        </div>

        <div v-if="hasFilter" class="active-filters">
          <span v-if="keyword" class="tag tag-brand">关键词：{{ keyword }}</span>
          <span v-if="activeCondition" class="tag tag-brand">成色：{{ activeCondition }}</span>
          <span v-if="activePriceLabel" class="tag tag-brand">价格：{{ activePriceLabel }}</span>
          <button class="btn-text" type="button" @click="resetFilters">清空筛选</button>
        </div>

        <ProductGrid
          :products="items"
          :loading="loading"
          :skeleton-count="10"
          :columns="4"
          empty-title="没有找到符合条件的商品"
          empty-description="试试更换关键词、放宽价格区间，或者看看最新上架"
        >
          <template #empty-action>
            <button class="btn btn-primary btn-sm" type="button" @click="resetFilters">清空筛选</button>
          </template>
        </ProductGrid>

        <AppPagination :page="page" :pages="pages" :total="total" :per-page="20" @change="goPage" />
      </section>
    </div>

    <div v-if="showFilter" class="mask" @click="showFilter = false" />
  </div>
</template>

<style scoped>
.list-page { padding-top: 18px; }
.crumb {
  display: flex; align-items: center; gap: 6px;
  color: var(--muted); font-size: 12.5px; margin-bottom: 14px;
}
.crumb a:hover { color: var(--brand); }

.layout { display: grid; grid-template-columns: 232px minmax(0, 1fr); gap: 20px; align-items: start; }

.filters {
  background: #fff; border: 1px solid var(--line); border-radius: var(--radius-lg);
  padding: 16px; position: sticky; top: 136px;
}
.filter-head { display: flex; align-items: center; gap: 10px; padding-bottom: 12px; border-bottom: 1px solid var(--line); }
.filter-head strong { font-size: 15px; }
.filter-head .btn-text { margin-left: auto; }
.close-mobile { display: none; border: none; background: none; color: var(--muted); padding: 2px; }

.filter-block { padding: 14px 0; border-bottom: 1px dashed var(--line); }
.filter-block:last-child { border-bottom: none; padding-bottom: 4px; }
.filter-block h4 { font-size: 12.5px; color: var(--muted); font-weight: 500; margin-bottom: 10px; }

.option {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 7px 10px; border: none; background: none;
  border-radius: 7px; color: var(--ink-2); font-size: 13.5px; text-align: left;
}
.option:hover { background: var(--hover); }
.option.on { background: var(--brand-soft); color: var(--brand); font-weight: 600; }
.count { font-size: 11px; color: var(--muted); }
.option.on .count { color: var(--brand); }

.chip-wrap { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  border: 1px solid var(--line-strong); background: #fff; color: var(--ink-2);
  border-radius: 999px; padding: 4px 11px; font-size: 12.5px;
}
.chip:hover { border-color: var(--brand); color: var(--brand); }
.chip.on { background: var(--brand); border-color: var(--brand); color: #fff; }

.price-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.price-inputs { display: flex; align-items: center; gap: 6px; color: var(--muted); }

.results { min-width: 0; }
.toolbar {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  background: #fff; border: 1px solid var(--line); border-radius: 12px;
  padding: 8px 14px; margin-bottom: 14px;
}
.sorts { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.sort {
  display: inline-flex; align-items: center; gap: 3px;
  border: none; background: none; padding: 6px 10px;
  border-radius: 7px; color: var(--ink-2); font-size: 13.5px;
}
.sort:hover { background: var(--hover); color: var(--brand); }
.sort.on { color: var(--brand); font-weight: 600; background: var(--brand-soft); }
.order { display: inline-flex; transition: transform .16s; }
.order.asc { transform: rotate(180deg); }
.order-toggle { margin-left: 4px; }
.toolbar-right { display: flex; align-items: center; gap: 12px; }
.filter-toggle {
  display: none; align-items: center; gap: 5px;
  border: 1px solid var(--line-strong); background: #fff;
  border-radius: 8px; padding: 5px 10px; font-size: 12.5px; color: var(--ink-2);
}

.active-filters { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }

.mask { display: none; }

@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  .filters {
    position: fixed; top: 0; left: 0; bottom: 0; z-index: 70;
    width: min(320px, 86vw); border-radius: 0; overflow-y: auto;
    transform: translateX(-100%); transition: transform .22s ease;
  }
  .filters.open { transform: none; }
  .close-mobile { display: block; margin-left: auto; }
  .filter-toggle { display: inline-flex; }
  .mask { display: block; position: fixed; inset: 0; background: rgba(15, 20, 28, .4); z-index: 60; }
}
</style>
