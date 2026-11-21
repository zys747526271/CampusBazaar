<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalogApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { useAppStore } from '@/stores/app'
import AppIcon from '@/components/ui/AppIcon.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const cart = useCartStore()
const app = useAppStore()

const keyword = ref(route.query.keyword || '')
const menuOpen = ref(false)
const suggestOpen = ref(false)
const suggestions = ref({ keywords: [], products: [] })
const menuRef = ref(null)
let suggestTimer = null

const initial = computed(() => (auth.user?.nickname || '同').slice(0, 1))
const isSeller = computed(() => auth.isSeller)

const navItems = computed(() => [
  { label: '首页', to: '/' },
  { label: '全部商品', to: '/products' },
  { label: isSeller.value ? '卖家中心' : '我要卖', to: '/seller' }
])

const onSearch = () => {
  const value = keyword.value.trim()
  suggestOpen.value = false
  router.push({ path: '/products', query: value ? { keyword: value } : {} })
}

const fetchSuggest = async () => {
  const value = keyword.value.trim()
  if (value.length < 1) {
    suggestions.value = { keywords: [], products: [] }
    suggestOpen.value = false
    return
  }
  try {
    suggestions.value = await catalogApi.suggest(value)
    suggestOpen.value = true
  } catch (error) {
    suggestOpen.value = false
  }
}

watch(keyword, () => {
  window.clearTimeout(suggestTimer)
  suggestTimer = window.setTimeout(fetchSuggest, 220)
})

watch(
  () => route.query.keyword,
  (value) => {
    keyword.value = value || ''
  }
)

const gotoProduct = (id) => {
  suggestOpen.value = false
  router.push(`/products/${id}`)
}

const gotoKeyword = (word) => {
  keyword.value = word
  onSearch()
}

const doLogout = async () => {
  menuOpen.value = false
  await auth.logout()
  cart.reset()
  app.reset()
  router.push('/')
}

const onDocumentClick = (event) => {
  if (menuRef.value && !menuRef.value.contains(event.target)) menuOpen.value = false
}

onMounted(async () => {
  document.addEventListener('click', onDocumentClick)
  if (auth.isLoggedIn) {
    try {
      await auth.fetchProfile()
      await Promise.all([cart.refresh(), app.loadUnread()])
    } catch (error) {
      /* 401 由拦截器统一处理 */
    }
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  window.clearTimeout(suggestTimer)
})
</script>

<template>
  <header class="site-header">
    <div class="topbar">
      <div class="container row-between">
        <p class="tagline">同校二手交易 · 自提或快递 · 交易留痕</p>
        <div class="top-links">
          <template v-if="auth.isLoggedIn">
            <RouterLink to="/orders">我的订单</RouterLink>
            <RouterLink to="/messages" class="with-dot">
              消息
              <i v-if="app.unread" class="dot" />
            </RouterLink>
            <RouterLink v-if="isSeller" to="/seller">卖家中心</RouterLink>
            <RouterLink v-else to="/seller">我要卖</RouterLink>
            <RouterLink v-if="auth.isAdmin" to="/admin">管理后台</RouterLink>
          </template>
          <template v-else>
            <RouterLink to="/login">登录</RouterLink>
            <RouterLink to="/register">注册</RouterLink>
          </template>
        </div>
      </div>
    </div>

    <div class="mainbar">
      <div class="container mainbar-inner">
        <RouterLink to="/" class="logo" aria-label="校园集市首页">
          <span class="logo-mark">
            <AppIcon name="shop" :size="20" />
          </span>
          <span class="logo-text">
            <strong>校园集市</strong>
            <small>CampusBazaar</small>
          </span>
        </RouterLink>

        <div class="search-wrap">
          <form class="search" @submit.prevent="onSearch">
            <AppIcon name="search" :size="17" class="search-icon" />
            <input
              v-model="keyword"
              type="search"
              placeholder="搜索教材、数码、宿舍好物…"
              maxlength="50"
              aria-label="搜索商品"
              @focus="keyword && fetchSuggest()"
            />
            <button class="search-btn" type="submit">搜索</button>
          </form>
          <Transition name="fade">
            <div v-if="suggestOpen && (suggestions.keywords.length || suggestions.products.length)" class="suggest">
              <div v-if="suggestions.keywords.length" class="suggest-tags">
                <button v-for="word in suggestions.keywords" :key="word" type="button" @click="gotoKeyword(word)">
                  <AppIcon name="search" :size="13" /> {{ word }}
                </button>
              </div>
              <button
                v-for="item in suggestions.products"
                :key="item.id"
                type="button"
                class="suggest-item"
                @click="gotoProduct(item.id)"
              >
                <span class="ellipsis">{{ item.name }}</span>
                <span class="price price-sm"><span class="unit">¥</span>{{ Number(item.price).toFixed(2) }}</span>
              </button>
            </div>
          </Transition>
        </div>

        <div class="actions">
          <RouterLink to="/messages" class="action" aria-label="消息">
            <AppIcon name="bell" :size="19" />
            <i v-if="app.unread" class="dot" />
            <span class="action-text hide-sm">消息</span>
          </RouterLink>
          <RouterLink to="/favorites" class="action" aria-label="收藏">
            <AppIcon name="heart" :size="19" />
            <span class="action-text hide-sm">收藏</span>
          </RouterLink>
          <RouterLink to="/cart" class="action" aria-label="购物车">
            <AppIcon name="cart" :size="20" />
            <i v-if="cart.count" class="badge cart-badge">{{ cart.badge }}</i>
            <span class="action-text hide-sm">购物车</span>
          </RouterLink>

          <div v-if="auth.isLoggedIn" ref="menuRef" class="user-menu">
            <button class="user-btn" type="button" @click.stop="menuOpen = !menuOpen">
              <img v-if="auth.avatar" :src="auth.avatar" alt="" class="avatar" />
              <span v-else class="avatar avatar-text">{{ initial }}</span>
              <span class="nickname hide-sm">{{ auth.displayName }}</span>
              <AppIcon name="chevron-down" :size="14" />
            </button>
            <Transition name="fade">
              <div v-if="menuOpen" class="menu">
                <RouterLink to="/profile" class="menu-item" @click="menuOpen = false">
                  <AppIcon name="user" :size="16" /> 个人中心
                </RouterLink>
                <RouterLink to="/orders" class="menu-item" @click="menuOpen = false">
                  <AppIcon name="file-text" :size="16" /> 我的订单
                </RouterLink>
                <RouterLink to="/favorites" class="menu-item" @click="menuOpen = false">
                  <AppIcon name="heart" :size="16" /> 我的收藏
                </RouterLink>
                <RouterLink to="/history" class="menu-item" @click="menuOpen = false">
                  <AppIcon name="clock" :size="16" /> 浏览记录
                </RouterLink>
                <RouterLink to="/balance" class="menu-item" @click="menuOpen = false">
                  <AppIcon name="wallet" :size="16" /> 我的余额
                </RouterLink>
                <RouterLink to="/seller" class="menu-item" @click="menuOpen = false">
                  <AppIcon name="shop" :size="16" /> {{ isSeller ? '卖家中心' : '开通卖家' }}
                </RouterLink>
                <div class="menu-divider" />
                <button class="menu-item danger" type="button" @click="doLogout">
                  <AppIcon name="logout" :size="16" /> 退出登录
                </button>
              </div>
            </Transition>
          </div>
          <div v-else class="auth-btns">
            <RouterLink to="/login" class="btn btn-sm">登录</RouterLink>
            <RouterLink to="/register" class="btn btn-primary btn-sm">注册</RouterLink>
          </div>
        </div>
      </div>
    </div>

    <nav class="navbar">
      <div class="container navbar-inner">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="nav-link">
          {{ item.label }}
        </RouterLink>
        <RouterLink to="/products?sort=sales" class="nav-link">热销榜</RouterLink>
        <span class="nav-tip">
          <AppIcon name="shield" :size="14" /> 同校交易 · 当面验货
        </span>
      </div>
    </nav>
  </header>
</template>

<style scoped>
.site-header {
  background: #fff;
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: 0;
  z-index: 40;
}

.topbar { background: #fafbfc; border-bottom: 1px solid var(--line); font-size: 12px; color: var(--muted); }
.topbar .container { height: 32px; }
.tagline { letter-spacing: .02em; }
.top-links { display: flex; align-items: center; gap: 16px; }
.top-links a { color: var(--ink-2); }
.top-links a:hover { color: var(--brand); }
.with-dot { position: relative; display: inline-flex; align-items: center; gap: 4px; }

.dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--brand);
  display: inline-block;
}

.mainbar-inner {
  display: flex; align-items: center; gap: 28px;
  height: 76px;
}

.logo { display: flex; align-items: center; gap: 10px; flex: none; }
.logo-mark {
  width: 40px; height: 40px; border-radius: 12px;
  background: linear-gradient(135deg, var(--brand-light), var(--brand));
  color: #fff; display: grid; place-items: center;
  box-shadow: 0 6px 16px rgba(255, 80, 0, .25);
}
.logo-text { display: flex; flex-direction: column; line-height: 1.15; }
.logo-text strong { font-size: 19px; letter-spacing: -.4px; }
.logo-text small { font-size: 10.5px; color: var(--muted); letter-spacing: .14em; text-transform: uppercase; }

.search-wrap { position: relative; flex: 1; max-width: 560px; }
.search {
  display: flex; align-items: center; gap: 8px;
  height: 44px; padding-left: 14px;
  border: 2px solid var(--brand);
  border-radius: var(--radius-pill);
  background: #fff;
  transition: box-shadow .16s;
}
.search:focus-within { box-shadow: 0 0 0 4px rgba(255, 80, 0, .1); }
.search-icon { color: var(--muted); }
.search input {
  flex: 1; min-width: 0; border: none; outline: none; background: none; font-size: 14px;
}
.search-btn {
  height: 36px; margin-right: 4px; padding: 0 22px;
  border: none; border-radius: var(--radius-pill);
  background: linear-gradient(135deg, var(--brand-light), var(--brand));
  color: #fff; font-weight: 600; font-size: 14px;
}
.search-btn:hover { background: linear-gradient(135deg, #ff8a5c, var(--brand-dark)); }

.suggest {
  position: absolute; top: calc(100% + 8px); left: 0; right: 0; z-index: 30;
  background: #fff; border-radius: 12px; border: 1px solid var(--line);
  box-shadow: var(--shadow); padding: 8px; overflow: hidden;
}
.suggest-tags { display: flex; flex-wrap: wrap; gap: 6px; padding: 6px 6px 10px; border-bottom: 1px dashed var(--line); }
.suggest-tags button {
  display: inline-flex; align-items: center; gap: 4px;
  border: none; background: var(--bg); color: var(--ink-2);
  border-radius: 999px; padding: 4px 10px; font-size: 12px;
}
.suggest-tags button:hover { background: var(--brand-soft); color: var(--brand); }
.suggest-item {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  width: 100%; padding: 9px 10px; border: none; background: none;
  text-align: left; font-size: 13.5px; border-radius: 8px;
}
.suggest-item:hover { background: var(--hover); }

.actions { display: flex; align-items: center; gap: 6px; margin-left: auto; }
.action {
  position: relative; display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 10px; border-radius: 10px; color: var(--ink-2); font-size: 13px;
}
.action:hover { background: var(--bg); color: var(--brand); }
.cart-badge { position: absolute; top: 0; right: 0; transform: translate(30%, -20%); }

.user-menu { position: relative; margin-left: 4px; }
.user-btn {
  display: flex; align-items: center; gap: 8px;
  border: 1px solid var(--line-strong); background: #fff;
  padding: 5px 10px 5px 6px; border-radius: var(--radius-pill);
  color: var(--ink-2); font-size: 13px;
}
.user-btn:hover { border-color: var(--brand); color: var(--brand); }
.avatar { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; }
.avatar-text {
  display: grid; place-items: center;
  background: linear-gradient(135deg, #ffd9c7, #ffb08a);
  color: #a03c0d; font-weight: 700; font-size: 13px;
}
.nickname { max-width: 96px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.menu {
  position: absolute; right: 0; top: calc(100% + 8px); z-index: 30;
  width: 186px; padding: 6px;
  background: #fff; border: 1px solid var(--line); border-radius: 12px;
  box-shadow: var(--shadow);
}
.menu-item {
  display: flex; align-items: center; gap: 9px; width: 100%;
  padding: 9px 10px; border: none; background: none;
  border-radius: 8px; color: var(--ink-2); font-size: 13.5px; text-align: left;
}
.menu-item:hover { background: var(--hover); color: var(--brand); }
.menu-item.danger:hover { background: var(--danger-soft); color: var(--danger); }
.menu-divider { height: 1px; background: var(--line); margin: 5px 4px; }

.auth-btns { display: flex; gap: 8px; margin-left: 6px; }

.navbar { border-top: 1px solid var(--line); }
.navbar-inner { display: flex; align-items: center; gap: 26px; height: 44px; }
.nav-link { color: var(--ink-2); font-size: 14px; position: relative; }
.nav-link::after {
  content: ''; position: absolute; left: 0; right: 0; bottom: -12px; height: 2px;
  background: var(--brand); transform: scaleX(0); transition: transform .16s;
}
.nav-link:hover, .nav-link.router-link-exact-active { color: var(--brand); font-weight: 500; }
.nav-link:hover::after, .nav-link.router-link-exact-active::after { transform: scaleX(1); }
.nav-tip {
  margin-left: auto; display: inline-flex; align-items: center; gap: 6px;
  color: var(--muted); font-size: 12px;
}

@media (max-width: 1080px) {
  .mainbar-inner { gap: 16px; }
  .logo-text small { display: none; }
}
@media (max-width: 880px) {
  .topbar { display: none; }
  .mainbar-inner { height: auto; padding: 12px 0; flex-wrap: wrap; gap: 12px; }
  .search-wrap { order: 3; flex-basis: 100%; max-width: none; }
  .actions { gap: 2px; }
  .navbar-inner { gap: 18px; overflow-x: auto; }
  .nav-tip { display: none; }
}
</style>
