<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { sellerApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { useToast } from '@/composables/useToast'
import ShopHeader from '@/components/layout/ShopHeader.vue'
import AppIcon from '@/components/ui/AppIcon.vue'

const auth = useAuthStore()
const app = useAppStore()
const route = useRoute()
const router = useRouter()
const { toastSuccess, toastError } = useToast()
const joining = ref(false)

const menus = [
  { label: '经营概览', to: '/seller', icon: 'chart', exact: true },
  { label: '我的商品', to: '/seller/products', icon: 'package' },
  { label: '发布商品', to: '/seller/products/new', icon: 'plus' },
  { label: '收到的订单', to: '/seller/orders', icon: 'truck' },
  { label: '自定义分类', to: '/seller/categories', icon: 'layers' },
  { label: '商品评价', to: '/seller/reviews', icon: 'message' }
]

const active = (item) => {
  if (item.exact) return route.path === item.to
  if (item.to === '/seller/products') {
    return route.path === '/seller/products' || /^\/seller\/products\/\d+\/edit$/.test(route.path)
  }
  return route.path === item.to || route.path.startsWith(item.to + '/')
}

const becomeSeller = async () => {
  joining.value = true
  try {
    await sellerApi.become()
    await auth.fetchProfile(true)
    app.loadUnread()
    toastSuccess('卖家身份已开通，去发布第一件商品吧')
    router.push('/seller/products/new')
  } catch (error) {
    toastError(error.message)
  } finally {
    joining.value = false
  }
}
</script>

<template>
  <div class="seller-shell">
    <ShopHeader />
    <div class="container seller-layout">
      <template v-if="auth.isSeller">
        <aside class="side">
          <div class="shop-card">
            <span class="avatar"><AppIcon name="shop" :size="18" /></span>
            <div>
              <strong>{{ auth.displayName }}的小店</strong>
              <p class="text-xs text-muted">校内面交 · 实时履约</p>
            </div>
          </div>
          <nav class="menu">
            <RouterLink
              v-for="item in menus"
              :key="item.to"
              :to="item.to"
              class="menu-item"
              :class="{ on: active(item) }"
            >
              <AppIcon :name="item.icon" :size="16" />
              <span>{{ item.label }}</span>
            </RouterLink>
          </nav>
          <RouterLink to="/seller/products/new" class="btn btn-primary btn-block publish">
            <AppIcon name="plus" :size="15" /> 发布新商品
          </RouterLink>
        </aside>
        <section class="content">
          <RouterView v-slot="{ Component }">
            <Transition name="fade" mode="out-in">
              <component :is="Component" />
            </Transition>
          </RouterView>
        </section>
      </template>

      <div v-else class="join panel">
        <div class="join-icon"><AppIcon name="shop" :size="30" /></div>
        <h2>开通卖家身份，把闲置变成现金</h2>
        <p class="text-muted">
          无需审核，一键开通。发布商品、接收订单、管理库存与评价，全部在卖家中心完成。
        </p>
        <ul class="benefits">
          <li><AppIcon name="check-circle" :size="16" /> 免费发布，卖出后货款进余额</li>
          <li><AppIcon name="check-circle" :size="16" /> 同校面交，免运费、当面验货</li>
          <li><AppIcon name="check-circle" :size="16" /> 经营看板，销量库存一目了然</li>
        </ul>
        <button class="btn btn-primary btn-lg" type="button" :disabled="joining" @click="becomeSeller">
          {{ joining ? '开通中…' : '立即开通卖家身份' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.seller-layout {
  display: grid; grid-template-columns: 220px minmax(0, 1fr);
  gap: 20px; padding-top: 24px; align-items: start;
}
.side {
  position: sticky; top: 136px;
  background: #fff; border: 1px solid var(--line); border-radius: var(--radius-lg);
  padding: 16px 14px;
}
.shop-card {
  display: flex; align-items: center; gap: 10px;
  padding: 4px 4px 14px; border-bottom: 1px solid var(--line);
}
.avatar {
  width: 40px; height: 40px; border-radius: 12px; flex: none;
  display: grid; place-items: center; color: #fff;
  background: linear-gradient(135deg, var(--brand-light), var(--brand));
}
.shop-card strong { font-size: 14px; }
.shop-card p { margin-top: 2px; }

.menu { display: flex; flex-direction: column; gap: 2px; margin-top: 12px; }
.menu-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: 9px; color: var(--ink-2); font-size: 13.5px;
}
.menu-item:hover { background: var(--hover); color: var(--brand); }
.menu-item.on { background: var(--brand-soft); color: var(--brand); font-weight: 600; }
.publish { margin-top: 16px; }

.content { min-width: 0; }

.join {
  grid-column: 1 / -1; max-width: 640px; margin: 40px auto;
  text-align: center; display: flex; flex-direction: column; align-items: center; gap: 14px;
  padding: 44px 32px;
}
.join-icon {
  width: 64px; height: 64px; border-radius: 20px; display: grid; place-items: center;
  background: var(--brand-soft); color: var(--brand);
}
.join h2 { font-size: 22px; }
.benefits { display: flex; flex-direction: column; gap: 8px; margin: 8px 0 10px; text-align: left; }
.benefits li { display: flex; align-items: center; gap: 8px; color: var(--ink-2); font-size: 13.5px; }
.benefits .app-icon { color: var(--ok); }

@media (max-width: 900px) {
  .seller-layout { grid-template-columns: 1fr; gap: 12px; }
  .side { position: static; }
  .shop-card { display: none; }
  .menu { flex-direction: row; overflow-x: auto; margin-top: 0; scrollbar-width: none; }
  .menu::-webkit-scrollbar { display: none; }
  .menu-item { white-space: nowrap; }
  .publish { display: none; }
}
</style>
