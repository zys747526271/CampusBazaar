<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalogApi, commentApi, favoriteApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppImage from '@/components/ui/AppImage.vue'
import AppRating from '@/components/ui/AppRating.vue'
import AppStepper from '@/components/ui/AppStepper.vue'
import AppModal from '@/components/ui/AppModal.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'
import AppPagination from '@/components/ui/AppPagination.vue'
import ProductGrid from '@/components/product/ProductGrid.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import StatusTag from '@/components/ui/StatusTag.vue'
import { REPORT_REASONS, dateTime, deliveryLabels, money, relativeTime } from '@/utils/format'
import { toastError, toastSuccess } from '@/composables/useToast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const cart = useCartStore()

const loading = ref(true)
const notFound = ref(false)
const product = ref(null)
const quantity = ref(1)
const activeImage = ref(0)
const busy = ref(false)

const reviews = ref([])
const reviewTotal = ref(0)
const reviewPage = ref(1)
const reviewPages = ref(0)
const reviewSort = ref('newest')
const reviewLoading = ref(false)

const reportOpen = ref(false)
const reportForm = ref({ reason: REPORT_REASONS[0], detail: '' })
const reportBusy = ref(false)

const images = computed(() => {
  const list = product.value?.images?.length ? product.value.images : [product.value?.cover_image].filter(Boolean)
  return list.length ? list : ['']
})
const seller = computed(() => product.value?.seller || {})
const rating = computed(() => product.value?.rating || { average: 0, total: 0, distribution: {} })
const canBuy = computed(() => Boolean(product.value?.can_buy))
const unavailableReason = computed(() => {
  if (!product.value) return ''
  if (product.value.status !== '已通过') return `商品${product.value.status}`
  if (product.value.quantity <= 0) return '商品已售罄'
  if (!product.value.is_available) return '商品已下架'
  return ''
})

const distribution = computed(() => {
  const dist = rating.value.distribution || {}
  const total = Math.max(rating.value.total || 0, 1)
  return [5, 4, 3, 2, 1].map((star) => ({
    star,
    count: dist[String(star)] || 0,
    percent: Math.round(((dist[String(star)] || 0) / total) * 100)
  }))
})

const loadProduct = async () => {
  loading.value = true
  notFound.value = false
  activeImage.value = 0
  quantity.value = 1
  try {
    product.value = await catalogApi.product(route.params.id)
    loadReviews(1)
  } catch (error) {
    notFound.value = true
    product.value = null
  } finally {
    loading.value = false
  }
}

const loadReviews = async (page = 1) => {
  reviewLoading.value = true
  try {
    const data = await catalogApi.comments(route.params.id, { page, per_page: 5, sort: reviewSort.value })
    reviews.value = data.items || []
    reviewTotal.value = data.total || 0
    reviewPage.value = data.page || 1
    reviewPages.value = data.pages || 0
  } catch (error) {
    reviews.value = []
  } finally {
    reviewLoading.value = false
  }
}

const requireLogin = (action) => {
  if (!auth.isLoggedIn) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return false
  }
  return true
}

const addToCart = async () => {
  if (!requireLogin()) return
  if (!canBuy.value) return
  busy.value = true
  try {
    await cart.add(product.value.id, quantity.value)
    toastSuccess('已加入购物车')
  } catch (error) {
    toastError(error.message)
  } finally {
    busy.value = false
  }
}

const buyNow = () => {
  if (!requireLogin()) return
  if (!canBuy.value) return
  router.push({ path: '/checkout', query: { product_id: product.value.id, quantity: quantity.value } })
}

const toggleFavorite = async () => {
  if (!requireLogin()) return
  try {
    if (product.value.favorited) {
      await favoriteApi.remove(product.value.id)
      product.value.favorited = false
      toastSuccess('已取消收藏')
    } else {
      await favoriteApi.add(product.value.id)
      product.value.favorited = true
      toastSuccess('已收藏')
    }
  } catch (error) {
    toastError(error.message)
  }
}

const likeReview = async (review) => {
  if (!requireLogin()) return
  try {
    const data = await commentApi.like(review.id)
    review.liked = data.liked
    review.like_count = data.like_count
  } catch (error) {
    toastError(error.message)
  }
}

const changeSort = (value) => {
  reviewSort.value = value
  loadReviews(1)
}

const submitReport = async () => {
  if (!requireLogin()) return
  reportBusy.value = true
  try {
    await commentApi.report({
      target_type: 'product',
      target_id: product.value.id,
      reason: reportForm.value.reason,
      detail: reportForm.value.detail
    })
    toastSuccess('举报已提交，管理员会尽快处理')
    reportOpen.value = false
    reportForm.value.detail = ''
  } catch (error) {
    toastError(error.message)
  } finally {
    reportBusy.value = false
  }
}

const preview = (index) => {
  const total = images.value.length
  activeImage.value = (index + total) % total
}

watch(() => route.params.id, loadProduct)
onMounted(loadProduct)
</script>

<template>
  <div class="container detail-page">
    <div v-if="loading" class="detail-skeleton">
      <div class="sk-gallery skeleton" />
      <div class="sk-info">
        <SkeletonBlock :h="26" w="80%" />
        <SkeletonBlock :h="40" w="45%" />
        <SkeletonBlock :h="18" w="60%" />
        <SkeletonBlock :h="18" w="70%" />
        <SkeletonBlock :h="46" w="100%" />
      </div>
    </div>

    <AppEmpty
      v-else-if="notFound"
      icon="package"
      title="商品不存在或已下架"
      description="它可能已被卖家下架、售出，或者链接有误"
    >
      <RouterLink to="/products" class="btn btn-primary btn-sm">去逛逛其他商品</RouterLink>
    </AppEmpty>

    <template v-else-if="product">
      <nav class="crumb">
        <RouterLink to="/">首页</RouterLink>
        <AppIcon name="chevron-right" :size="12" />
        <RouterLink to="/products">全部商品</RouterLink>
        <template v-if="product.tag">
          <AppIcon name="chevron-right" :size="12" />
          <RouterLink :to="{ path: '/products', query: { tag_id: product.tag.id } }">{{ product.tag.name }}</RouterLink>
        </template>
        <AppIcon name="chevron-right" :size="12" />
        <span class="ellipsis crumb-current">{{ product.name }}</span>
      </nav>

      <section class="top">
        <div class="gallery">
          <div class="main-img">
            <AppImage :src="images[activeImage]" :alt="product.name" :ratio="'1 / 1'" radius="14px" />
            <button v-if="images.length > 1" class="nav prev" type="button" aria-label="上一张" @click="preview(activeImage - 1)">
              <AppIcon name="chevron-left" :size="18" />
            </button>
            <button v-if="images.length > 1" class="nav next" type="button" aria-label="下一张" @click="preview(activeImage + 1)">
              <AppIcon name="chevron-right" :size="18" />
            </button>
            <span class="img-index">{{ activeImage + 1 }} / {{ images.length }}</span>
          </div>
          <div v-if="images.length > 1" class="thumbs">
            <button
              v-for="(image, index) in images"
              :key="index"
              type="button"
              class="thumb"
              :class="{ on: index === activeImage }"
              @click="activeImage = index"
            >
              <AppImage :src="image" :alt="`${product.name} 图 ${index + 1}`" radius="8px" />
            </button>
          </div>
        </div>

        <div class="info">
          <div class="title-row">
            <h1>{{ product.name }}</h1>
            <StatusTag v-if="product.status !== '已通过' || !product.is_available" :status="product.status" kind="product" />
          </div>

          <div class="meta-row">
            <span class="tag tag-line">{{ product.condition }}</span>
            <span v-for="label in deliveryLabels(product)" :key="label" class="tag tag-line">{{ label }}</span>
            <span v-if="product.location" class="meta-item"><AppIcon name="map-pin" :size="13" /> {{ product.location }}</span>
            <span class="meta-item"><AppIcon name="eye" :size="13" /> {{ product.views }} 次浏览</span>
            <span class="meta-item">已售 {{ product.sales }}</span>
          </div>

          <div class="price-box">
            <div class="price-main">
              <span class="price price-lg"><span class="unit">¥</span>{{ money(product.price) }}</span>
              <span v-if="product.original_price" class="origin">原价 ¥{{ money(product.original_price) }}</span>
              <span v-if="product.discount" class="tag tag-brand">{{ product.discount.toFixed(1) }} 折</span>
            </div>
            <div class="price-tip">
              <AppIcon name="shield" :size="14" />
              {{ product.supports_pickup ? '校内自提 · 当面验货' : '快递发货 · 验货后再确认收货' }} · 确认收货后货款才结算给卖家
            </div>
          </div>

          <div class="buy-row">
            <div class="qty">
              <span class="label">数量</span>
              <AppStepper v-model="quantity" :min="1" :max="Math.max(product.quantity, 1)" :disabled="!canBuy" />
              <span class="stock">库存 {{ product.quantity }} 件</span>
            </div>
          </div>

          <div v-if="!canBuy" class="alert alert-warn">
            <AppIcon name="alert" :size="16" />
            <span v-if="product.is_owner">这是你发布的商品，可前往卖家中心编辑或下架。</span>
            <span v-else>{{ unavailableReason }}，暂时无法购买。</span>
          </div>

          <div v-if="product.is_owner" class="actions">
            <RouterLink :to="`/seller/products/${product.id}/edit`" class="btn btn-primary btn-lg">
              <AppIcon name="edit" :size="17" /> 编辑商品
            </RouterLink>
            <RouterLink to="/seller/products" class="btn btn-lg">管理我的商品</RouterLink>
          </div>
          <div v-else class="actions">
            <button class="btn btn-primary btn-lg grow" type="button" :disabled="!canBuy || busy" @click="buyNow">
              立即购买
            </button>
            <button class="btn btn-lg grow" type="button" :disabled="!canBuy || busy" @click="addToCart">
              <AppIcon name="cart" :size="17" /> 加入购物车
            </button>
            <button class="btn btn-lg btn-icon" :class="{ 'btn-ghost': product.favorited }" type="button" @click="toggleFavorite">
              <AppIcon name="heart" :size="18" :filled="product.favorited" />
            </button>
          </div>

          <div class="delivery-box">
            <div class="d-row">
              <span class="d-label">自提</span>
              <template v-if="product.supports_pickup">
                <span>{{ product.pickup_location || '卖家下单后补充自提点' }}</span>
                <span class="d-note">当面验货，可约定自提时间</span>
              </template>
              <span v-else class="text-muted">该商品不支持自提</span>
            </div>
            <div class="d-row">
              <span class="d-label">快递</span>
              <template v-if="product.supports_express">
                <span v-if="product.free_shipping" class="d-free">包邮</span>
                <span v-else class="d-fee">运费 ¥{{ money(product.shipping_fee) }}</span>
                <span class="d-note">下单时自动计入总价，仅支持在线支付</span>
              </template>
              <span v-else class="text-muted">该商品不支持快递</span>
            </div>
          </div>

          <div class="seller-card">
            <RouterLink :to="`/shops/${seller.id}`" class="seller-main">
              <span class="avatar">
                <img v-if="seller.avatar_url" :src="seller.avatar_url" alt="" />
                <template v-else>{{ (seller.nickname || '同').slice(0, 1) }}</template>
              </span>
              <div class="seller-text">
                <strong>{{ seller.nickname || '校内同学' }}</strong>
                <div class="seller-meta">
                  <AppRating :model-value="seller.rating || 0" :size="12" readonly />
                  <span v-if="seller.rating" class="text-xs text-muted">{{ seller.rating }} 分</span>
                  <span class="text-xs text-muted">· 在售 {{ seller.product_count || 0 }}</span>
                  <span class="text-xs text-muted">· 成交 {{ seller.sold_count || 0 }}</span>
                </div>
              </div>
              <span class="enter">进店逛逛 <AppIcon name="chevron-right" :size="13" /></span>
            </RouterLink>
          </div>

          <div class="promise">
            <span><AppIcon name="check-circle" :size="14" /> 同校自提</span>
            <span><AppIcon name="check-circle" :size="14" /> 当面验货</span>
            <span><AppIcon name="check-circle" :size="14" /> 订单留痕</span>
            <button class="report-link" type="button" @click="reportOpen = true">
              <AppIcon name="alert" :size="13" /> 举报
            </button>
          </div>
        </div>
      </section>

      <section class="panel desc">
        <h2 class="block-title">商品描述</h2>
        <p class="desc-text">{{ product.description || '卖家没有填写更多描述，可以在下单前通过订单备注或线下沟通确认细节。' }}</p>
        <div class="desc-meta">
          <span>发布时间：{{ dateTime(product.created_at) }}</span>
          <span v-if="product.seller_category">卖家分类：{{ product.seller_category.name }}</span>
        </div>
      </section>

      <section class="panel reviews">
        <div class="review-head">
          <h2 class="block-title">商品评价 <span class="text-sm text-muted">（{{ reviewTotal }}）</span></h2>
          <div class="review-sorts">
            <button type="button" :class="{ on: reviewSort === 'newest' }" @click="changeSort('newest')">最新</button>
            <button type="button" :class="{ on: reviewSort === 'helpful' }" @click="changeSort('helpful')">最有帮助</button>
            <button type="button" :class="{ on: reviewSort === 'rating' }" @click="changeSort('rating')">评分最高</button>
          </div>
        </div>

        <div class="review-top">
          <div class="score">
            <strong>{{ rating.total ? rating.average : '—' }}</strong>
            <AppRating :model-value="rating.average" :size="14" readonly />
            <span class="text-xs text-muted">{{ rating.total }} 条评价</span>
          </div>
          <div class="distribution">
            <div v-for="row in distribution" :key="row.star" class="dist-row">
              <span class="star-label">{{ row.star }} 星</span>
              <div class="bar"><i :style="{ width: `${row.percent}%` }" /></div>
              <span class="count">{{ row.count }}</span>
            </div>
          </div>
        </div>

        <div v-if="reviewLoading" class="review-loading">
          <SkeletonBlock v-for="i in 2" :key="i" :h="70" radius="10px" />
        </div>
        <AppEmpty
          v-else-if="!reviews.length"
          icon="message"
          title="还没有评价"
          description="确认收货后就可以留下第一条评价"
          compact
        />
        <ul v-else class="review-list">
          <li v-for="review in reviews" :key="review.id" class="review">
            <span class="r-avatar">
              <img v-if="review.user?.avatar_url" :src="review.user.avatar_url" alt="" />
              <template v-else>{{ (review.user?.nickname || '同').slice(0, 1) }}</template>
            </span>
            <div class="r-body">
              <div class="r-head">
                <strong>{{ review.user?.nickname || '匿名同学' }}</strong>
                <AppRating :model-value="review.rating" :size="12" readonly />
                <span class="text-xs text-muted">{{ relativeTime(review.created_at) }}</span>
              </div>
              <p class="r-content">{{ review.content || '该同学没有填写文字评价' }}</p>
              <div v-if="review.images?.length" class="r-images">
                <AppImage v-for="(img, i) in review.images" :key="i" :src="img" :ratio="'1 / 1'" radius="8px" />
              </div>
              <div v-if="review.seller_reply" class="r-reply">
                <strong>卖家回复：</strong>{{ review.seller_reply }}
              </div>
              <div class="r-foot">
                <button type="button" class="like" :class="{ on: review.liked }" @click="likeReview(review)">
                  <AppIcon name="heart" :size="14" :filled="review.liked" /> 有用 {{ review.like_count || 0 }}
                </button>
              </div>
            </div>
          </li>
        </ul>

        <AppPagination :page="reviewPage" :pages="reviewPages" :total="reviewTotal" :per-page="5" @change="loadReviews" />
      </section>

      <section v-if="product.related?.length" class="section">
        <div class="section-head">
          <h2 class="section-title">看了又看</h2>
          <RouterLink to="/products" class="more-link">更多商品 <AppIcon name="chevron-right" :size="14" /></RouterLink>
        </div>
        <ProductGrid :products="product.related" :columns="5" />
      </section>
    </template>

    <div v-if="product && !product.is_owner && canBuy" class="mobile-buy">
      <div class="mb-price">
        <span class="price price-md"><span class="unit">¥</span>{{ money(product.price) }}</span>
        <span class="text-xs text-muted">库存 {{ product.quantity }}</span>
      </div>
      <button class="btn" type="button" :disabled="busy" @click="addToCart">加入购物车</button>
      <button class="btn btn-primary" type="button" :disabled="busy" @click="buyNow">立即购买</button>
    </div>

    <AppModal v-model="reportOpen" title="举报商品" width="440px">
      <div class="field mb-12">
        <label>举报原因</label>
        <select v-model="reportForm.reason" class="select">
          <option v-for="reason in REPORT_REASONS" :key="reason" :value="reason">{{ reason }}</option>
        </select>
      </div>
      <div class="field">
        <label>补充说明（选填）</label>
        <textarea v-model="reportForm.detail" class="textarea" maxlength="500" placeholder="描述具体问题，便于管理员核实" />
      </div>
      <template #footer>
        <button class="btn" type="button" @click="reportOpen = false">取消</button>
        <button class="btn btn-primary" type="button" :disabled="reportBusy" @click="submitReport">
          {{ reportBusy ? '提交中…' : '提交举报' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.detail-page { padding-top: 18px; }

.crumb { display: flex; align-items: center; gap: 6px; color: var(--muted); font-size: 12.5px; margin-bottom: 14px; }
.crumb a:hover { color: var(--brand); }
.crumb-current { max-width: 320px; }

.detail-skeleton { display: grid; grid-template-columns: 460px 1fr; gap: 28px; }
.sk-gallery { aspect-ratio: 1 / 1; border-radius: 14px; }
.sk-info { display: flex; flex-direction: column; gap: 14px; }

.top { display: grid; grid-template-columns: 460px minmax(0, 1fr); gap: 28px; }

.gallery { display: flex; flex-direction: column; gap: 10px; }
.main-img { position: relative; border-radius: 14px; overflow: hidden; background: #fff; border: 1px solid var(--line); }
.nav {
  position: absolute; top: 50%; transform: translateY(-50%);
  width: 34px; height: 34px; border-radius: 50%;
  border: none; background: rgba(255, 255, 255, .86); color: var(--ink-2);
  display: grid; place-items: center; box-shadow: var(--shadow-xs);
  opacity: 0; transition: opacity .16s;
}
.main-img:hover .nav { opacity: 1; }
.nav.prev { left: 10px; }
.nav.next { right: 10px; }
.img-index {
  position: absolute; right: 12px; bottom: 12px;
  background: rgba(15, 20, 28, .55); color: #fff;
  font-size: 11.5px; padding: 2px 8px; border-radius: 999px;
}
.thumbs { display: flex; gap: 8px; }
.thumb {
  width: 68px; padding: 0; border: 2px solid transparent;
  border-radius: 9px; overflow: hidden; background: none;
}
.thumb.on { border-color: var(--brand); }

.info { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.title-row { display: flex; align-items: flex-start; gap: 10px; }
.title-row h1 { font-size: 23px; line-height: 1.45; font-weight: 600; letter-spacing: -.2px; }

.meta-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; color: var(--muted); font-size: 12.5px; }
.meta-item { display: inline-flex; align-items: center; gap: 4px; }

.price-box {
  background: linear-gradient(120deg, #fff6f0, #fff0e6);
  border-radius: 12px; padding: 16px 18px;
}
.price-main { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.origin { color: var(--muted); font-size: 13px; text-decoration: line-through; }
.price-tip {
  display: flex; align-items: center; gap: 6px;
  margin-top: 8px; color: #8a5a3c; font-size: 12px;
}

.buy-row { display: flex; align-items: center; gap: 16px; }
.qty { display: flex; align-items: center; gap: 10px; }
.qty .label { color: var(--muted); font-size: 13px; }
.stock { color: var(--muted); font-size: 12.5px; }

.actions { display: flex; gap: 10px; flex-wrap: wrap; }
.actions .grow { flex: 1; min-width: 140px; }

.delivery-box { border: 1px solid var(--line); border-radius: 10px; background: #fafbfc; padding: 10px 14px; display: flex; flex-direction: column; gap: 8px; }
.d-row { display: flex; align-items: center; gap: 10px; font-size: 13px; flex-wrap: wrap; }
.d-label { color: var(--muted); width: 36px; flex: none; }
.d-note { color: var(--muted); font-size: 12px; }
.d-free { color: #0f7b57; background: #e7f7f0; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.d-fee { color: #b54708; background: #fff4e5; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.seller-card { border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; background: #fff; }
.seller-main { display: flex; align-items: center; gap: 10px; }
.avatar {
  width: 38px; height: 38px; border-radius: 50%; flex: none;
  display: grid; place-items: center; font-weight: 700; color: #a03c0d;
  background: linear-gradient(135deg, #ffe2d3, #ffc3a6); overflow: hidden;
}
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.seller-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.seller-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.enter { margin-left: auto; color: var(--muted); font-size: 12.5px; display: inline-flex; align-items: center; gap: 2px; }
.seller-main:hover .enter { color: var(--brand); }

.promise {
  display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
  color: var(--muted); font-size: 12px;
}
.promise span { display: inline-flex; align-items: center; gap: 4px; }
.promise .app-icon { color: var(--ok); }
.report-link {
  margin-left: auto; display: inline-flex; align-items: center; gap: 4px;
  border: none; background: none; color: var(--muted-2); font-size: 12px;
}
.report-link:hover { color: var(--danger); }

.block-title { font-size: 16px; font-weight: 600; }
.desc { margin-top: 20px; }
.desc-text { margin-top: 12px; color: var(--ink-2); line-height: 1.9; white-space: pre-wrap; }
.desc-meta { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 16px; color: var(--muted); font-size: 12px; }

.reviews { margin-top: 16px; }
.review-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.review-sorts { display: flex; gap: 6px; }
.review-sorts button {
  border: 1px solid var(--line-strong); background: #fff; color: var(--ink-2);
  border-radius: 999px; padding: 4px 12px; font-size: 12.5px;
}
.review-sorts button.on { border-color: var(--brand); color: var(--brand); background: var(--brand-soft); }

.review-top {
  display: grid; grid-template-columns: 180px 1fr; gap: 24px;
  padding: 18px 0; margin-top: 12px; border-bottom: 1px dashed var(--line);
}
.score { display: flex; flex-direction: column; gap: 6px; }
.score strong { font-size: 34px; color: var(--brand); line-height: 1; font-variant-numeric: tabular-nums; }
.distribution { display: flex; flex-direction: column; gap: 6px; max-width: 420px; }
.dist-row { display: flex; align-items: center; gap: 10px; font-size: 12px; color: var(--muted); }
.star-label { width: 34px; flex: none; }
.bar { flex: 1; height: 6px; border-radius: 999px; background: #f1f3f7; overflow: hidden; }
.bar i { display: block; height: 100%; background: linear-gradient(90deg, #ffb37a, var(--brand)); border-radius: 999px; }
.count { width: 28px; text-align: right; }

.review-loading { display: flex; flex-direction: column; gap: 10px; padding-top: 16px; }
.review-list { display: flex; flex-direction: column; }
.review { display: flex; gap: 12px; padding: 18px 0; border-bottom: 1px solid var(--line); }
.review:last-child { border-bottom: none; }
.r-avatar {
  width: 36px; height: 36px; border-radius: 50%; flex: none;
  display: grid; place-items: center; font-size: 13px; font-weight: 700;
  background: #eef1f6; color: var(--ink-2); overflow: hidden;
}
.r-avatar img { width: 100%; height: 100%; object-fit: cover; }
.r-body { flex: 1; min-width: 0; }
.r-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.r-head strong { font-size: 13.5px; }
.r-content { margin-top: 6px; color: var(--ink-2); line-height: 1.75; }
.r-images { display: flex; gap: 8px; margin-top: 8px; }
.r-images > * { width: 84px; }
.r-reply {
  margin-top: 8px; background: #fafbfc; border-radius: 8px;
  padding: 8px 10px; font-size: 12.5px; color: var(--ink-2);
}
.r-reply strong { color: var(--brand); font-weight: 500; }
.r-foot { margin-top: 8px; }
.like {
  display: inline-flex; align-items: center; gap: 5px;
  border: none; background: none; color: var(--muted); font-size: 12px;
}
.like:hover, .like.on { color: var(--brand); }

.more-link { display: inline-flex; align-items: center; gap: 2px; color: var(--muted); font-size: 13px; }
.more-link:hover { color: var(--brand); }

.mobile-buy { display: none; }

.mobile-buy { display: none; }

@media (max-width: 1000px) {
  .top, .detail-skeleton { grid-template-columns: 1fr; }
  .main-img { max-width: 520px; }
  .review-top { grid-template-columns: 1fr; gap: 14px; }
}
@media (max-width: 720px) {
  .detail-page { padding-bottom: 72px; }
  .mobile-buy {
    position: fixed; left: 0; right: 0; bottom: 56px; z-index: 44;
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px;
    background: rgba(255, 255, 255, .97);
    backdrop-filter: blur(10px);
    border-top: 1px solid var(--line);
  }
  .mb-price { display: flex; flex-direction: column; line-height: 1.2; margin-right: 4px; }
  .mobile-buy .btn { flex: 1; height: 40px; padding: 0 12px; }
  .title-row h1 { font-size: 19px; }
  .actions .btn-lg { height: 42px; font-size: 14.5px; }
  .thumbs .thumb { width: 56px; }
  .desc-meta { gap: 10px; }
}
</style>
