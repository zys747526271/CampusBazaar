<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { catalogApi } from '@/api'
import ProductGrid from '@/components/product/ProductGrid.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import AppRating from '@/components/ui/AppRating.vue'
import AppImage from '@/components/ui/AppImage.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { dateOnly, dateTime } from '@/utils/format'

const route = useRoute()
const loading = ref(true)
const shop = ref(null)
const notFound = ref(false)
const products = ref([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const sort = ref('created_at')

const stats = computed(() => shop.value?.stats || {})
const reviews = ref([])
const reviewSummary = ref({ average: 0, total: 0, distribution: {} })
const reviewPage = ref(1)
const reviewPages = ref(0)
const reviewTotal = ref(0)
const reviewLoading = ref(false)

const load = async () => {
  loading.value = true
  notFound.value = false
  try {
    shop.value = await catalogApi.shop(route.params.id)
    await Promise.all([loadProducts(1), loadReviews(1)])
  } catch (error) {
    notFound.value = true
  } finally {
    loading.value = false
  }
}

const loadProducts = async (nextPage = page.value) => {
  const data = await catalogApi.shopProducts(route.params.id, { page: nextPage, per_page: 12, sort: sort.value })
  products.value = data.items || []
  total.value = data.total || 0
  pages.value = data.pages || 0
  page.value = data.page || 1
}

const loadReviews = async (nextPage = 1) => {
  reviewLoading.value = true
  try {
    const data = await catalogApi.shopComments(route.params.id, { page: nextPage, per_page: 8 })
    reviews.value = data.items || []
    reviewSummary.value = data.summary || { average: 0, total: 0, distribution: {} }
    reviewTotal.value = data.total || 0
    reviewPages.value = data.pages || 0
    reviewPage.value = data.page || 1
  } catch (error) {
    reviews.value = []
  } finally {
    reviewLoading.value = false
  }
}

const changeSort = (value) => {
  sort.value = value
  loadProducts(1)
}

watch(() => route.params.id, load)
onMounted(load)
</script>

<template>
  <div class="container shop-page">
    <div v-if="loading" class="shop-card">
      <SkeletonBlock :h="64" :w="64" circle />
      <div class="grow">
        <SkeletonBlock :h="20" w="180px" />
        <SkeletonBlock :h="14" w="260px" class="mt-12" />
      </div>
    </div>

    <AppEmpty v-else-if="notFound" icon="shop" title="店铺不存在" description="该卖家可能还未开通店铺">
      <RouterLink to="/products" class="btn btn-primary btn-sm">去逛逛</RouterLink>
    </AppEmpty>

    <template v-else>
      <section class="shop-card">
        <span class="avatar">
          <img v-if="shop.avatar_url" :src="shop.avatar_url" alt="" />
          <template v-else>{{ (shop.nickname || '同').slice(0, 1) }}</template>
        </span>
        <div class="shop-main">
          <div class="shop-name">
            <h1>{{ shop.nickname }}的小店</h1>
            <span class="tag tag-brand">校园卖家</span>
          </div>
          <p class="text-sm text-muted">
            {{ shop.campus || '校内' }} · {{ dateOnly(shop.seller_since) }} 开店
          </p>
        </div>
        <div class="shop-stats">
          <div><strong>{{ stats.on_sale_count || 0 }}</strong><span>在售商品</span></div>
          <div><strong>{{ stats.sold_count || 0 }}</strong><span>累计成交</span></div>
          <div>
            <strong class="rate">
              <AppRating :model-value="stats.rating || 0" :size="13" readonly />
              {{ stats.rating || '—' }}
            </strong>
            <span>卖家评分</span>
          </div>
        </div>
      </section>

      <div class="toolbar">
        <div class="sorts">
          <button type="button" :class="{ on: sort === 'created_at' }" @click="changeSort('created_at')">最新上架</button>
          <button type="button" :class="{ on: sort === 'sales' }" @click="changeSort('sales')">销量优先</button>
          <button type="button" :class="{ on: sort === 'price' }" @click="changeSort('price')">价格</button>
        </div>
        <span class="text-sm text-muted">共 {{ total }} 件在售</span>
      </div>

      <ProductGrid
        :products="products"
        :skeleton-count="8"
        :columns="4"
        empty-title="这家店还没有在售商品"
        empty-description="稍后再来看看，或者去首页逛逛"
      >
        <template #empty-action>
          <RouterLink to="/products" class="btn btn-primary btn-sm">去首页逛逛</RouterLink>
        </template>
      </ProductGrid>

      <AppPagination :page="page" :pages="pages" :total="total" :per-page="12" @change="loadProducts" />

      <section class="reviews">
        <div class="reviews-head">
          <h2>店铺评价</h2>
          <div v-if="reviewSummary.total" class="review-score">
            <strong>{{ reviewSummary.average }}</strong>
            <AppRating :model-value="reviewSummary.average" :size="14" readonly />
            <span class="text-sm text-muted">共 {{ reviewSummary.total }} 条 · 含已售出与已下架商品</span>
          </div>
          <span v-else class="text-sm text-muted">暂无评价，卖出商品后买家评价会展示在这里</span>
        </div>

        <div v-if="reviewLoading" class="review-skeleton">
          <SkeletonBlock :h="72" />
          <SkeletonBlock :h="72" />
        </div>
        <AppEmpty v-else-if="!reviews.length" icon="comment" title="还没有评价" compact />

        <ul v-else class="review-list">
          <li v-for="review in reviews" :key="review.id" class="review">
            <div class="review-top">
              <span class="avatar sm">{{ (review.user?.nickname || '同').slice(0, 1) }}</span>
              <strong>{{ review.user?.nickname || '匿名同学' }}</strong>
              <AppRating :model-value="review.rating" :size="12" readonly />
              <span class="text-xs text-muted">{{ dateTime(review.created_at) }}</span>
            </div>
            <p class="review-text">{{ review.content || '（未填写文字评价）' }}</p>
            <RouterLink v-if="review.product" :to="`/products/${review.product.id}`" class="review-product">
              <AppImage :src="review.product.cover_image" :alt="review.product.name" radius="6px" class="rp-img" />
              <span class="ellipsis">{{ review.product.name }}</span>
              <span class="tag tag-line">{{ review.product.is_on_sale ? '在售' : '已结束' }}</span>
            </RouterLink>
            <p v-if="review.seller_reply" class="review-reply">卖家回复：{{ review.seller_reply }}</p>
          </li>
        </ul>

        <AppPagination
          v-if="reviewPages > 1"
          :page="reviewPage"
          :pages="reviewPages"
          :total="reviewTotal"
          :per-page="8"
          @change="loadReviews"
        />
      </section>
    </template>
  </div>
</template>

<style scoped>
.shop-page { padding-top: 24px; }
.shop-card {
  display: flex; align-items: center; gap: 18px;
  background: linear-gradient(120deg, #fff, #fff8f4);
  border: 1px solid var(--line); border-radius: var(--radius-lg);
  padding: 24px 28px;
}
.avatar {
  width: 64px; height: 64px; border-radius: 20px; flex: none;
  display: grid; place-items: center; font-size: 24px; font-weight: 700; color: #a03c0d;
  background: linear-gradient(135deg, #ffe2d3, #ffc3a6); overflow: hidden;
}
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.shop-name { display: flex; align-items: center; gap: 10px; }
.shop-name h1 { font-size: 22px; letter-spacing: -.2px; }
.shop-main p { margin-top: 4px; }
.shop-stats { display: flex; gap: 28px; margin-left: auto; }
.shop-stats div { text-align: center; }
.shop-stats strong { display: block; font-size: 20px; font-variant-numeric: tabular-nums; }
.shop-stats .rate { display: flex; align-items: center; gap: 5px; justify-content: center; font-size: 16px; }
.shop-stats span { font-size: 11.5px; color: var(--muted); }

.toolbar {
  display: flex; align-items: center; justify-content: space-between;
  margin: 18px 0 14px;
}
.sorts { display: flex; gap: 4px; background: #fff; border: 1px solid var(--line); border-radius: 10px; padding: 3px; }
.sorts button {
  border: none; background: none; padding: 6px 14px; border-radius: 8px;
  color: var(--ink-2); font-size: 13px;
}
.sorts button.on { background: var(--brand-soft); color: var(--brand); font-weight: 600; }

.reviews { margin-top: 28px; }
.reviews-head { display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.reviews-head h2 { font-size: 18px; }
.review-score { display: flex; align-items: center; gap: 8px; }
.review-score strong { font-size: 20px; color: var(--brand); }
.review-skeleton { display: flex; flex-direction: column; gap: 10px; }
.review-list { display: flex; flex-direction: column; gap: 10px; }
.review { background: #fff; border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
.review-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 13px; }
.review-top .text-xs { margin-left: auto; }
.avatar.sm { width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; font-size: 11px; font-weight: 700; background: linear-gradient(135deg, #ffe2d3, #ffc3a6); color: #a03c0d; }
.review-text { margin: 8px 0; font-size: 13.5px; line-height: 1.7; color: var(--ink-2); }
.review-product { display: inline-flex; align-items: center; gap: 8px; background: #fafbfc; border-radius: 8px; padding: 6px 8px; font-size: 12.5px; color: var(--ink-2); max-width: 100%; }
.rp-img { width: 28px; flex: none; }
.review-reply { margin-top: 8px; font-size: 12.5px; color: var(--muted); background: #f7f8fa; border-radius: 6px; padding: 6px 10px; }

@media (max-width: 760px) {
  .shop-card { flex-wrap: wrap; padding: 18px; gap: 12px; }
  .shop-stats { margin-left: 0; width: 100%; justify-content: space-between; gap: 8px; }
  .shop-name h1 { font-size: 18px; }
}
</style>
