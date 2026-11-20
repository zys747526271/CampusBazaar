<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'
import ShopHeader from '@/components/layout/ShopHeader.vue'
import ShopFooter from '@/components/layout/ShopFooter.vue'
import AppIcon from '@/components/ui/AppIcon.vue'

const route = useRoute()
const showTop = ref(false)

const onScroll = () => {
  showTop.value = window.scrollY > 600
}

onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))

const isActive = (path) => (path === '/' ? route.path === '/' : route.path.startsWith(path))

const scrollTop = () => window.scrollTo({ top: 0, behavior: 'smooth' })
</script>

<template>
  <div class="shop-shell">
    <ShopHeader />
    <main class="shop-main">
      <RouterView v-slot="{ Component }">
        <Transition name="fade" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
    <ShopFooter />

    <Transition name="fade">
      <button v-if="showTop" class="back-top" type="button" aria-label="回到顶部" @click="scrollTop">
        <AppIcon name="chevron-down" :size="18" class="rotate" />
      </button>
    </Transition>

    <nav class="mobile-nav">
      <RouterLink to="/" :class="{ on: isActive('/') }">
        <AppIcon name="home" :size="20" /><span>首页</span>
      </RouterLink>
      <RouterLink to="/products" :class="{ on: isActive('/products') }">
        <AppIcon name="grid" :size="20" /><span>逛逛</span>
      </RouterLink>
      <RouterLink to="/cart" :class="{ on: isActive('/cart') }">
        <AppIcon name="cart" :size="20" /><span>购物车</span>
      </RouterLink>
      <RouterLink to="/profile" :class="{ on: isActive('/profile') || isActive('/orders') }">
        <AppIcon name="user" :size="20" /><span>我的</span>
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.shop-shell { min-height: 100vh; display: flex; flex-direction: column; }
.shop-main { flex: 1; padding-bottom: 24px; }

.back-top {
  position: fixed; right: 28px; bottom: 36px; z-index: 35;
  width: 44px; height: 44px; border-radius: 50%;
  border: 1px solid var(--line); background: #fff; color: var(--ink-2);
  display: grid; place-items: center; box-shadow: var(--shadow-sm);
}
.back-top:hover { color: var(--brand); border-color: var(--brand); }
.rotate { transform: rotate(180deg); }

.mobile-nav { display: none; }

@media (max-width: 720px) {
  .back-top { display: none; }
  .shop-main { padding-bottom: 68px; }
  .mobile-nav {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 45;
    display: grid; grid-template-columns: repeat(4, 1fr);
    background: rgba(255, 255, 255, .96); backdrop-filter: blur(12px);
    border-top: 1px solid var(--line);
    padding-bottom: env(safe-area-inset-bottom);
  }
  .mobile-nav a {
    display: flex; flex-direction: column; align-items: center; gap: 3px;
    padding: 8px 0 6px; color: var(--muted); font-size: 10.5px;
  }
  .mobile-nav a.on { color: var(--brand); }
}
</style>
