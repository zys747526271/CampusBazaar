<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { catalogApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { useCartStore } from '@/stores/cart'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppImage from '@/components/ui/AppImage.vue'
import ProductGrid from '@/components/product/ProductGrid.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import { money, relativeTime } from '@/utils/format'

const auth = useAuthStore()
const app = useAppStore()
const cart = useCartStore()

const loading = ref(true)
const data = ref({ banners: [], tags: [], blocks: { recommended: [], hot: [], latest: [] } })
const bannerIndex = ref(0)
let bannerTimer = null

const banners = computed(() => data.value.banners || [])
const tags = computed(() => data.value.tags || [])
const recommended = computed(() => data.value.blocks?.recommended || [])
const hot = computed(() => data.value.blocks?.hot || [])
const latest = computed(() => data.value.blocks?.latest || [])
const onSaleCount = computed(() => tags.value.reduce((sum, tag) => sum + (tag.product_count || 0), 0))

const serviceItems = [
  { icon: 'shield', title: '校内实名', desc: '同校同学，身份可查' },
  { icon: 'map-pin', title: '当面自提', desc: '约在图书馆、宿舍楼下' },
  { icon: 'file-text', title: '订单留痕', desc: '每笔交易都有记录' },
  { icon: 'star', title: '评价可查', desc: '看历史评价再下单' }
]

const startBanner = () => {
  stopBanner()
  if (banners.value.length <= 1) return
  bannerTimer = window.setInterval(() => {
    bannerIndex.value = (bannerIndex.value + 1) % banners.value.length
  }, 5200)
}

const stopBanner = () => {
  if (bannerTimer) window.clearInterval(bannerTimer)
  bannerTimer = null
}

const goBanner = (index) => {
  bannerIndex.value = index
  startBanner()
}

const linkOf = (banner) => banner.link_url || '/products'

onMounted(async () => {
  try {
    data.value = await catalogApi.home()
    startBanner()
  } catch (error) {
    /* 首屏失败时保留空态，避免整页白屏 */
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(stopBanner)
</script>

<template>
  <div class="home">
    <div class="container">
      <!-- 首屏：分类 + 轮播 + 我的面板 -->
      <section class="hero">
        <aside class="cat-rail">
          <div class="rail-head">
            <AppIcon name="grid" :size="15" /> 全部分类
          </div>
          <RouterLink
            v-for="tag in tags"
            :key="tag.id"
            :to="{ path: '/products', query: { tag_id: tag.id } }"
            class="cat-item"
          >
            <span class="cat-name">{{ tag.name }}</span>
            <span class="cat-count">{{ tag.product_count || 0 }}</span>
          </RouterLink>
          <div v-if="!tags.length" class="rail-empty">
            <SkeletonBlock v-for="i in 5" :key="i" :h="14" w="70%" />
          </div>
          <RouterLink to="/seller/products/new" class="rail-cta">
            <span class="rail-cta-icon"><AppIcon name="gift" :size="17" /></span>
            <div>
              <strong>闲置变现</strong>
              <small>免费发布 · 同校自提</small>
            </div>
            <AppIcon name="chevron-right" :size="14" class="rail-cta-arrow" />
          </RouterLink>
          <RouterLink to="/products" class="rail-more">
            浏览全部商品 <AppIcon name="arrow-right" :size="13" />
          </RouterLink>
        </aside>

        <div class="banner-wrap">
          <div class="banner">
            <template v-if="banners.length">
              <RouterLink
                v-for="(banner, index) in banners"
                :key="banner.id"
                :to="linkOf(banner)"
                class="slide"
                :class="{ active: index === bannerIndex }"
              >
                <img :src="banner.image_url" :alt="banner.title" />
              </RouterLink>
              <div class="dots">
                <button
                  v-for="(banner, index) in banners"
                  :key="`dot-${banner.id}`"
                  type="button"
                  :class="{ on: index === bannerIndex }"
                  :aria-label="`第 ${index + 1} 张`"
                  @click="goBanner(index)"
                />
              </div>
            </template>
            <div v-else class="banner-skeleton skeleton" />
          </div>
          <div class="quick-row">
            <RouterLink to="/products?sort=sales" class="quick">
              <span class="quick-icon hot"><AppIcon name="trend-up" :size="18" /></span>
              <div><strong>热销榜</strong><small>同学们都在买</small></div>
            </RouterLink>
            <RouterLink to="/products?sort=created_at" class="quick">
              <span class="quick-icon new"><AppIcon name="clock" :size="18" /></span>
              <div><strong>最新上架</strong><small>刚发布的好物</small></div>
            </RouterLink>
            <RouterLink to="/seller" class="quick">
              <span class="quick-icon sell"><AppIcon name="shop" :size="18" /></span>
              <div><strong>我要卖</strong><small>闲置快速出手</small></div>
            </RouterLink>
          </div>
        </div>

        <aside class="me-panel">
          <div class="me">
            <template v-if="auth.isLoggedIn">
              <span class="avatar">
                <img v-if="auth.avatar" :src="auth.avatar" alt="" />
                <template v-else>{{ (auth.displayName || '同').slice(0, 1) }}</template>
              </span>
              <div class="me-text">
                <strong>{{ auth.displayName }}</strong>
                <span class="text-xs text-muted">欢迎回来</span>
              </div>
            </template>
            <template v-else>
              <span class="avatar guest"><AppIcon name="user" :size="20" /></span>
              <div class="me-text">
                <strong>你好，同学</strong>
                <span class="text-xs text-muted">登录后查看订单与收藏</span>
              </div>
            </template>
          </div>
          <div class="me-actions">
            <RouterLink to="/orders" class="mini">
              <AppIcon name="file-text" :size="17" /><span>我的订单</span>
            </RouterLink>
            <RouterLink to="/favorites" class="mini">
              <AppIcon name="heart" :size="17" /><span>我的收藏</span>
            </RouterLink>
            <RouterLink to="/cart" class="mini">
              <AppIcon name="cart" :size="17" /><span>购物车</span>
              <em v-if="cart.count">{{ cart.badge }}</em>
            </RouterLink>
            <RouterLink to="/seller" class="mini">
              <AppIcon name="shop" :size="17" /><span>{{ auth.isSeller ? '卖家中心' : '我要卖' }}</span>
            </RouterLink>
          </div>
          <div v-if="!auth.isLoggedIn" class="me-login">
            <RouterLink to="/login" class="btn btn-primary btn-block btn-sm">登录 / 注册</RouterLink>
          </div>

          <div class="notice">
            <div class="notice-head">
              <AppIcon name="bell" :size="14" /> 平台公告
            </div>
            <ul>
              <li>交易请尽量选择校内自提，当面验货。</li>
              <li>线下支付订单需卖家确认收款后发货。</li>
              <li>遇到违规商品可在详情页举报。</li>
            </ul>
          </div>

          <div class="stats">
            <div><strong>{{ onSaleCount }}</strong><span>在售好物</span></div>
            <div><strong>{{ tags.length }}</strong><span>商品分类</span></div>
          </div>
        </aside>
      </section>

      <!-- 服务承诺 -->
      <section class="services">
        <div v-for="item in serviceItems" :key="item.title" class="service">
          <span class="service-icon"><AppIcon :name="item.icon" :size="18" /></span>
          <div>
            <strong>{{ item.title }}</strong>
            <small>{{ item.desc }}</small>
          </div>
        </div>
      </section>

      <!-- 为你推荐 -->
      <section class="section">
        <div class="section-head">
          <div>
            <h2 class="section-title">为你推荐</h2>
            <p class="section-sub">按浏览、成交与运营加权挑选的校内好物</p>
          </div>
          <RouterLink to="/products?sort=sales" class="more-link">
            查看更多 <AppIcon name="chevron-right" :size="14" />
          </RouterLink>
        </div>
        <ProductGrid :products="recommended" :loading="loading" :skeleton-count="10" :columns="5" />
      </section>

      <!-- 热门好物 -->
      <section class="section">
        <div class="section-head">
          <div>
            <h2 class="section-title">热门好物</h2>
            <p class="section-sub">成交量与浏览量最高的商品</p>
          </div>
          <RouterLink to="/products?sort=sales" class="more-link">
            更多热销 <AppIcon name="chevron-right" :size="14" />
          </RouterLink>
        </div>
        <ProductGrid :products="hot" :loading="loading" :skeleton-count="8" :columns="4" />
      </section>

      <!-- 最新上架 -->
      <section class="section">
        <div class="section-head">
          <div>
            <h2 class="section-title">最新上架</h2>
            <p class="section-sub">刚刚发布的闲置，先到先得</p>
          </div>
          <RouterLink to="/products?sort=created_at" class="more-link">
            全部上新 <AppIcon name="chevron-right" :size="14" />
          </RouterLink>
        </div>
        <div class="latest-grid">
          <template v-if="loading">
            <div v-for="i in 6" :key="i" class="latest-card">
              <SkeletonBlock :h="96" :w="96" radius="10px" />
              <div class="latest-body">
                <SkeletonBlock :h="14" w="80%" />
                <SkeletonBlock :h="12" w="50%" />
                <SkeletonBlock :h="18" w="35%" />
              </div>
            </div>
          </template>
          <template v-else>
            <RouterLink
              v-for="item in latest.slice(0, 6)"
              :key="item.id"
              :to="`/products/${item.id}`"
              class="latest-card"
            >
              <AppImage :src="item.cover_image" :alt="item.name" :ratio="'1 / 1'" radius="10px" class="latest-img" />
              <div class="latest-body">
                <h3 class="clamp-2">{{ item.name }}</h3>
                <p class="text-xs text-muted">{{ item.location || '校内自提' }} · {{ relativeTime(item.created_at) }}</p>
                <div class="latest-price">
                  <span class="price price-sm"><span class="unit">¥</span>{{ money(item.price) }}</span>
                  <span class="tag tag-line">{{ item.condition }}</span>
                </div>
              </div>
            </RouterLink>
          </template>
        </div>
      </section>

      <!-- 卖家招募 -->
      <section class="join-banner">
        <div class="join-text">
          <span class="tag tag-brand">毕业季 · 清仓季</span>
          <h2>把闲置挂上来，让它去找下一个主人</h2>
          <p>免费发布 · 一键开通卖家 · 卖出后货款进余额</p>
        </div>
        <RouterLink to="/seller" class="btn btn-dark btn-lg">
          <AppIcon name="shop" :size="17" /> 立即开通卖家
        </RouterLink>
      </section>
    </div>
  </div>
</template>

<style scoped>
.home { padding-top: 20px; }

/* ---------- hero ---------- */
.hero {
  display: grid;
  grid-template-columns: 216px minmax(0, 1fr) 248px;
  gap: 16px;
  align-items: stretch;
}

.cat-rail {
  background: #fff; border: 1px solid var(--line); border-radius: var(--radius-lg);
  padding: 12px 8px; display: flex; flex-direction: column;
}
.rail-head {
  display: flex; align-items: center; gap: 7px;
  padding: 4px 10px 10px; font-weight: 600; font-size: 13.5px;
  border-bottom: 1px solid var(--line); margin-bottom: 6px;
}
.cat-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 10px; border-radius: 8px; color: var(--ink-2); font-size: 13.5px;
}
.cat-item:hover { background: var(--brand-soft); color: var(--brand); }
.cat-count { font-size: 11.5px; color: var(--muted); }
.cat-item:hover .cat-count { color: var(--brand); }
.rail-empty { display: flex; flex-direction: column; gap: 10px; padding: 8px 10px; }
.rail-cta {
  margin-top: auto; display: flex; align-items: center; gap: 10px;
  padding: 12px; border-radius: 10px;
  background: linear-gradient(120deg, #fff4ee, #ffe7d9);
  color: #8a4a22;
}
.rail-cta:hover { background: linear-gradient(120deg, #ffefe5, #ffdcc8); }
.rail-cta-icon {
  width: 32px; height: 32px; border-radius: 9px; flex: none;
  display: grid; place-items: center; background: #fff; color: var(--brand);
}
.rail-cta strong { display: block; font-size: 13px; }
.rail-cta small { font-size: 11px; opacity: .8; }
.rail-cta-arrow { margin-left: auto; opacity: .55; }

.rail-more {
  padding: 10px; font-size: 12.5px; color: var(--muted);
  display: inline-flex; align-items: center; gap: 4px;
}
.rail-more:hover { color: var(--brand); }

.banner-wrap { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.banner {
  position: relative; flex: 1; min-height: 320px;
  border-radius: var(--radius-lg); overflow: hidden; background: #eceff4;
}
.slide { position: absolute; inset: 0; opacity: 0; transition: opacity .5s ease; }
.slide.active { opacity: 1; }
.slide img { width: 100%; height: 100%; object-fit: cover; }
.banner-skeleton { position: absolute; inset: 0; }
.dots {
  position: absolute; bottom: 14px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 6px; padding: 5px 8px; border-radius: 999px;
  background: rgba(15, 20, 28, .28); backdrop-filter: blur(6px);
}
.dots button {
  width: 7px; height: 7px; border-radius: 999px; border: none;
  background: rgba(255, 255, 255, .55); padding: 0; transition: all .2s;
}
.dots button.on { width: 18px; background: #fff; }

.quick-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.quick {
  display: flex; align-items: center; gap: 10px;
  background: #fff; border: 1px solid var(--line); border-radius: 12px;
  padding: 12px 14px; transition: all .16s;
}
.quick:hover { border-color: var(--brand); transform: translateY(-2px); box-shadow: var(--shadow-sm); }
.quick-icon {
  width: 36px; height: 36px; border-radius: 11px; display: grid; place-items: center; flex: none;
}
.quick-icon.hot { background: #fff0e8; color: var(--brand); }
.quick-icon.new { background: var(--info-soft); color: var(--info); }
.quick-icon.sell { background: var(--ok-soft); color: var(--ok); }
.quick strong { display: block; font-size: 13.5px; }
.quick small { color: var(--muted); font-size: 11.5px; }

.me-panel {
  background: #fff; border: 1px solid var(--line); border-radius: var(--radius-lg);
  padding: 16px; display: flex; flex-direction: column;
}
.me { display: flex; align-items: center; gap: 10px; }
.avatar {
  width: 44px; height: 44px; border-radius: 50%; flex: none;
  display: grid; place-items: center; font-weight: 700; color: #a03c0d;
  background: linear-gradient(135deg, #ffe2d3, #ffc3a6); overflow: hidden;
}
.avatar.guest { background: #f0f2f6; color: var(--muted); }
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.me-text { display: flex; flex-direction: column; line-height: 1.35; min-width: 0; }
.me-text strong { font-size: 14.5px; }
.me-login { margin-top: 10px; }

.me-actions {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 14px;
}
.mini {
  position: relative;
  display: flex; flex-direction: column; align-items: center; gap: 5px;
  padding: 10px 6px; border-radius: 10px; background: #fafbfc;
  color: var(--ink-2); font-size: 12px;
}
.mini:hover { background: var(--brand-soft); color: var(--brand); }
.mini em {
  position: absolute; top: 4px; right: 8px;
  font-style: normal; font-size: 10px; font-weight: 700;
  color: #fff; background: var(--brand); border-radius: 999px; padding: 0 5px;
}

.notice { margin-top: 16px; border-top: 1px dashed var(--line); padding-top: 12px; }
.notice-head { display: flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 600; margin-bottom: 8px; }
.notice li { font-size: 12px; color: var(--muted); line-height: 1.7; padding-left: 12px; position: relative; }
.notice li::before {
  content: ''; position: absolute; left: 2px; top: 9px;
  width: 4px; height: 4px; border-radius: 50%; background: #d3d8e0;
}
.stats { display: flex; gap: 10px; margin-top: auto; padding-top: 14px; }
.stats div {
  flex: 1; text-align: center; background: #fafbfc; border-radius: 10px; padding: 8px 4px;
}
.stats strong { display: block; font-size: 18px; color: var(--brand); font-variant-numeric: tabular-nums; }
.stats span { font-size: 11px; color: var(--muted); }

/* ---------- services ---------- */
.services {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
  margin-top: 16px; background: #fff; border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 16px 20px;
}
.service { display: flex; align-items: center; gap: 10px; }
.service-icon {
  width: 36px; height: 36px; border-radius: 11px; flex: none;
  display: grid; place-items: center; background: var(--brand-soft); color: var(--brand);
}
.service strong { display: block; font-size: 13px; }
.service small { color: var(--muted); font-size: 11.5px; }

.more-link {
  display: inline-flex; align-items: center; gap: 2px;
  color: var(--muted); font-size: 13px;
}
.more-link:hover { color: var(--brand); }

/* ---------- latest ---------- */
.latest-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.latest-card {
  display: flex; gap: 12px; padding: 12px;
  background: #fff; border: 1px solid var(--line); border-radius: 12px;
  transition: all .16s;
}
.latest-card:hover { border-color: transparent; box-shadow: var(--shadow-sm); transform: translateY(-2px); }
.latest-img { width: 96px; flex: none; }
.latest-body { display: flex; flex-direction: column; gap: 5px; min-width: 0; flex: 1; }
.latest-body h3 { font-size: 13.5px; font-weight: 500; line-height: 1.45; }
.latest-price { display: flex; align-items: center; justify-content: space-between; margin-top: auto; }

/* ---------- join ---------- */
.join-banner {
  margin-top: 40px; padding: 32px 36px;
  border-radius: var(--radius-lg);
  background: linear-gradient(120deg, #fff3ec, #ffe7d9 60%, #ffd9c4);
  display: flex; align-items: center; justify-content: space-between; gap: 24px;
}
.join-text h2 { font-size: 24px; margin: 10px 0 6px; letter-spacing: -.3px; }
.join-text p { color: #8a5a3c; font-size: 13.5px; }

@media (max-width: 1080px) {
  .hero { grid-template-columns: 200px minmax(0, 1fr); }
  .me-panel { display: none; }
  .banner { min-height: 280px; }
  .latest-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 760px) {
  .hero { grid-template-columns: 1fr; }
  .cat-rail { flex-direction: row; overflow-x: auto; padding: 8px; gap: 4px; }
  .rail-head, .rail-more, .rail-cta { display: none; }
  .cat-item { white-space: nowrap; padding: 6px 12px; background: #f7f8fa; }
  .cat-count { display: none; }
  .banner { min-height: 200px; }
  .quick-row { grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .quick { flex-direction: column; text-align: center; padding: 10px 6px; gap: 6px; }
  .quick small { display: none; }
  .services { grid-template-columns: repeat(2, 1fr); gap: 14px; padding: 14px; }
  .latest-grid { grid-template-columns: 1fr; }
  .join-banner { flex-direction: column; align-items: flex-start; padding: 22px; }
  .join-text h2 { font-size: 19px; }
}
</style>
