<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppIcon from '@/components/ui/AppIcon.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const open = ref(false)

const groups = [
  {
    title: '运营',
    items: [
      { label: '控制台', to: '/admin', icon: 'chart', exact: true },
      { label: '订单管理', to: '/admin/orders', icon: 'truck' }
    ]
  },
  {
    title: '内容治理',
    items: [
      { label: '商品管理', to: '/admin/products', icon: 'package' },
      { label: '评价管理', to: '/admin/comments', icon: 'message' },
      { label: '举报处理', to: '/admin/reports', icon: 'alert' }
    ]
  },
  {
    title: '账号',
    items: [
      { label: '用户管理', to: '/admin/users', icon: 'user' },
      { label: '商家管理', to: '/admin/sellers', icon: 'shop' }
    ]
  },
  {
    title: '站点',
    items: [
      { label: '平台分类', to: '/admin/tags', icon: 'tag' },
      { label: '首页轮播', to: '/admin/banners', icon: 'image' },
      { label: '操作审计', to: '/admin/audit', icon: 'shield' }
    ]
  }
]

const current = computed(() => {
  const flat = groups.flatMap((g) => g.items)
  return flat.find((item) => (item.exact ? route.path === item.to : route.path.startsWith(item.to)))?.label || '控制台'
})

const isActive = (item) => (item.exact ? route.path === item.to : route.path.startsWith(item.to))

const logout = () => {
  auth.adminLogout()
  router.replace('/admin/login')
}
</script>

<template>
  <div class="admin-shell">
    <aside class="sidebar" :class="{ open }">
      <div class="brand">
        <span class="brand-mark"><AppIcon name="shield" :size="18" /></span>
        <div class="brand-text">
          <strong>校园集市</strong>
          <small>管理后台</small>
        </div>
      </div>

      <nav class="nav">
        <div v-for="group in groups" :key="group.title" class="nav-group">
          <p class="nav-title">{{ group.title }}</p>
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="nav-item"
            :class="{ on: isActive(item) }"
            @click="open = false"
          >
            <AppIcon :name="item.icon" :size="16" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </div>
      </nav>

      <div class="side-foot">
        <RouterLink to="/" class="nav-item subtle">
          <AppIcon name="logout" :size="16" />
          <span>返回商城前台</span>
        </RouterLink>
      </div>
    </aside>

    <div v-if="open" class="backdrop" @click="open = false" />

    <div class="main">
      <header class="topbar">
        <div class="left">
          <button class="menu-toggle" type="button" aria-label="菜单" @click="open = !open">
            <AppIcon name="list" :size="18" />
          </button>
          <span class="crumb">控制台 / {{ current }}</span>
        </div>
        <div class="right">
          <span class="who">
            <span class="avatar">{{ (auth.admin?.name || '管').slice(0, 1) }}</span>
            {{ auth.admin?.name || auth.admin?.username || '管理员' }}
            <span class="tag tag-brand">{{ auth.admin?.permission_level || '普通' }}</span>
          </span>
          <button class="btn btn-sm" type="button" @click="logout">退出</button>
        </div>
      </header>

      <main class="content">
        <RouterView v-slot="{ Component }">
          <Transition name="fade" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-shell { display: flex; min-height: 100vh; background: #f4f6f9; }

.sidebar {
  width: 224px; flex: none;
  background: #12161f; color: #cbd3df;
  display: flex; flex-direction: column;
  position: sticky; top: 0; height: 100vh;
  padding: 18px 12px;
}
.brand { display: flex; align-items: center; gap: 10px; padding: 4px 8px 18px; }
.brand-mark {
  width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center;
  background: linear-gradient(135deg, var(--brand-light), var(--brand)); color: #fff;
}
.brand-text { display: flex; flex-direction: column; line-height: 1.2; }
.brand-text strong { color: #fff; font-size: 15px; }
.brand-text small { font-size: 11px; color: #7b8697; letter-spacing: .1em; }

.nav { flex: 1; overflow-y: auto; }
.nav-group { margin-bottom: 14px; }
.nav-title {
  font-size: 10.5px; letter-spacing: .12em; color: #66707f;
  text-transform: uppercase; padding: 6px 12px;
}
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 9px;
  color: #c2cad6; font-size: 13.5px; margin-bottom: 2px;
  transition: background .14s, color .14s;
}
.nav-item:hover { background: rgba(255, 255, 255, .06); color: #fff; }
.nav-item.on { background: linear-gradient(135deg, rgba(255, 122, 69, .22), rgba(255, 80, 0, .16)); color: #ffb38a; }
.nav-item.subtle { color: #8b95a5; }
.side-foot { border-top: 1px solid rgba(255, 255, 255, .07); padding-top: 10px; }

.main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.topbar {
  height: 60px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; background: #fff; border-bottom: 1px solid var(--line);
  position: sticky; top: 0; z-index: 20;
}
.left { display: flex; align-items: center; gap: 12px; }
.crumb { color: var(--muted); font-size: 13px; }
.menu-toggle { display: none; border: 1px solid var(--line-strong); background: #fff; border-radius: 8px; padding: 6px; }
.right { display: flex; align-items: center; gap: 14px; }
.who { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--ink-2); }
.avatar {
  width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center;
  background: #eef1f6; color: var(--ink-2); font-size: 12px; font-weight: 700;
}
.content { padding: 22px 24px 40px; }

.backdrop { display: none; }

@media (max-width: 980px) {
  .sidebar {
    position: fixed; left: 0; top: 0; z-index: 50; transform: translateX(-100%);
    transition: transform .2s ease;
  }
  .sidebar.open { transform: none; }
  .backdrop { display: block; position: fixed; inset: 0; background: rgba(15, 20, 28, .4); z-index: 40; }
  .menu-toggle { display: grid; place-items: center; }
  .content { padding: 16px 14px 32px; }
  .crumb { display: none; }
}
</style>
