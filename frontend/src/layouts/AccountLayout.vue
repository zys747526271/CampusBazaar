<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import AppIcon from '@/components/ui/AppIcon.vue'

const route = useRoute()
const auth = useAuthStore()
const app = useAppStore()

const menus = computed(() => [
  { label: '个人中心', to: '/profile', icon: 'user' },
  { label: '我的订单', to: '/orders', icon: 'file-text' },
  { label: '我的收藏', to: '/favorites', icon: 'heart' },
  { label: '浏览记录', to: '/history', icon: 'clock' },
  { label: '收货地址', to: '/addresses', icon: 'map-pin' },
  { label: '我的余额', to: '/balance', icon: 'wallet' },
  { label: '我的消息', to: '/messages', icon: 'bell', badge: app.unread }
])

const active = (path) => route.path === path || route.path.startsWith(`${path}/`)
</script>

<template>
  <div class="container account-layout">
    <aside class="side">
      <div class="who">
        <span class="avatar">
          <img v-if="auth.avatar" :src="auth.avatar" alt="" />
          <template v-else>{{ (auth.displayName || '同').slice(0, 1) }}</template>
        </span>
        <div class="who-text">
          <strong>{{ auth.displayName }}</strong>
          <span class="text-xs text-muted">{{ auth.isSeller ? '卖家 · 买家' : '买家' }}</span>
        </div>
      </div>
      <nav class="menu">
        <RouterLink v-for="item in menus" :key="item.to" :to="item.to" class="menu-item" :class="{ on: active(item.to) }">
          <AppIcon :name="item.icon" :size="16" />
          <span>{{ item.label }}</span>
          <span v-if="item.badge" class="badge">{{ item.badge }}</span>
        </RouterLink>
      </nav>
    </aside>

    <section class="content">
      <RouterView v-slot="{ Component }">
        <Transition name="fade" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </section>
  </div>
</template>

<style scoped>
.account-layout {
  display: grid; grid-template-columns: 216px minmax(0, 1fr);
  gap: 20px; padding-top: 24px; align-items: start;
}
.side {
  background: #fff; border: 1px solid var(--line); border-radius: var(--radius-lg);
  padding: 18px 14px; position: sticky; top: 136px;
}
.who { display: flex; align-items: center; gap: 10px; padding: 4px 6px 16px; border-bottom: 1px solid var(--line); }
.avatar {
  width: 42px; height: 42px; border-radius: 50%; flex: none;
  display: grid; place-items: center; font-weight: 700; color: #a03c0d;
  background: linear-gradient(135deg, #ffe2d3, #ffc3a6); overflow: hidden;
}
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.who-text { display: flex; flex-direction: column; line-height: 1.4; min-width: 0; }
.who-text strong { font-size: 14.5px; }

.menu { display: flex; flex-direction: column; gap: 2px; margin-top: 12px; }
.menu-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: 9px; color: var(--ink-2); font-size: 13.5px;
}
.menu-item:hover { background: var(--hover); color: var(--brand); }
.menu-item.on { background: var(--brand-soft); color: var(--brand); font-weight: 600; }
.menu-item .badge { margin-left: auto; }

.content { min-width: 0; }

@media (max-width: 900px) {
  .account-layout { grid-template-columns: 1fr; gap: 12px; }
  .side { position: static; padding: 12px; }
  .who { display: none; }
  .menu { flex-direction: row; overflow-x: auto; margin-top: 0; gap: 6px; scrollbar-width: none; }
  .menu::-webkit-scrollbar { display: none; }
  .menu-item { white-space: nowrap; padding: 8px 12px; }
}
</style>
