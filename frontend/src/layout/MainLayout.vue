<template>
  <div class="main-layout">
    <header class="header">
      <div class="container">
        <router-link to="/" class="logo">
          <el-icon><Shop /></el-icon>
          <h1>校园集市</h1>
        </router-link>

        <nav class="nav-links">
          <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">首页</router-link>
          <router-link to="/products" class="nav-item">全部商品</router-link>
          <router-link v-if="userStore.isSeller" to="/seller" class="nav-item">卖家中心</router-link>
        </nav>

        <div class="search-bar">
          <el-input v-model="searchQuery" placeholder="搜索校园好物" @keyup.enter="handleSearch">
            <template #append>
              <el-button @click="handleSearch"><el-icon><Search /></el-icon></el-button>
            </template>
          </el-input>
        </div>

        <div class="nav-actions">
          <template v-if="userStore.isAuthenticated">
            <router-link to="/cart" class="nav-icon" title="购物车">
              <el-badge :value="cartCount" :hidden="cartCount === 0">
                <el-icon :size="20"><ShoppingCart /></el-icon>
              </el-badge>
            </router-link>
            <el-dropdown trigger="click" @command="handleCommand">
              <span class="user-dropdown">
                <el-avatar :size="34" :src="userStore.avatar">{{ userStore.displayName.charAt(0).toUpperCase() }}</el-avatar>
                <span class="user-name">{{ userStore.displayName }}</span>
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile"><el-icon><User /></el-icon>个人中心</el-dropdown-item>
                  <el-dropdown-item command="orders"><el-icon><List /></el-icon>我的订单</el-dropdown-item>
                  <el-dropdown-item command="favorites"><el-icon><Star /></el-icon>我的收藏</el-dropdown-item>
                  <el-dropdown-item command="history"><el-icon><Clock /></el-icon>浏览记录</el-dropdown-item>
                  <el-dropdown-item command="seller" divided v-if="userStore.isSeller">
                    <el-icon><Sell /></el-icon>卖家中心
                  </el-dropdown-item>
                  <el-dropdown-item command="become-seller" divided v-else>
                    <el-icon><Sell /></el-icon>成为卖家
                  </el-dropdown-item>
                  <el-dropdown-item command="admin" v-if="userStore.isAdmin">
                    <el-icon><Setting /></el-icon>管理工作台
                  </el-dropdown-item>
                  <el-dropdown-item command="logout" divided><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <router-link to="/auth/login" class="nav-item">登录</router-link>
            <router-link to="/auth/register" class="nav-item register-btn">注册</router-link>
          </template>
        </div>
      </div>
    </header>

    <main class="main-content">
      <div class="container"><router-view /></div>
    </main>

    <footer class="footer">
      <div class="container">
        <p>校园集市 · 让闲置流转，让校园更环保 &copy; {{ new Date().getFullYear() }}</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import api from '../utils/api'
import {
  Shop, Search, ShoppingCart, ArrowDown, User, List, Star, Clock,
  Sell, Setting, SwitchButton
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const searchQuery = ref('')
const cartCount = ref(0)

const fetchCartCount = async () => {
  if (!userStore.isAuthenticated) { cartCount.value = 0; return }
  try {
    const resp = await api.cart.getItems()
    const items = resp.data || []
    cartCount.value = items.length
  } catch (e) {
    cartCount.value = 0
  }
}

const handleSearch = () => {
  const q = searchQuery.value.trim()
  router.push({ path: '/products', query: q ? { search: q } : {} })
}

const handleCommand = async (command) => {
  switch (command) {
    case 'profile': router.push('/profile'); break
    case 'orders': router.push('/orders'); break
    case 'favorites': router.push('/favorites'); break
    case 'history': router.push('/history'); break
    case 'seller': router.push('/seller'); break
    case 'admin': router.push('/admin'); break
    case 'logout':
      userStore.logout()
      ElMessage.success('已退出登录')
      router.push('/')
      break
    case 'become-seller': {
      const res = await userStore.becomeSeller()
      if (res.success) {
        ElMessage.success('已开通卖家身份，欢迎入驻！')
        router.push('/seller')
      } else {
        ElMessage.error(res.message || '开通失败')
      }
      break
    }
  }
}

onMounted(fetchCartCount)
watch(() => route.fullPath, () => {
  if (route.query.search) searchQuery.value = route.query.search
  fetchCartCount()
})
</script>

<style lang="scss" scoped>
.main-layout { display: flex; flex-direction: column; min-height: 100vh; }
.container { width: 100%; max-width: 1200px; margin: 0 auto; padding: 0 16px; }

.header {
  background: #fff;
  box-shadow: 0 2px 10px rgba(0,0,0,.06);
  position: sticky; top: 0; z-index: 100;
  .container { display: flex; align-items: center; height: 68px; gap: 24px; }
  .logo {
    display: flex; align-items: center; gap: 6px; text-decoration: none; color: #409eff;
    flex-shrink: 0;
    .el-icon { font-size: 24px; }
    h1 { font-size: 21px; font-weight: 700; white-space: nowrap; }
  }
  .nav-links { display: flex; gap: 18px; flex-shrink: 0;
    .nav-item { color: #606266; text-decoration: none; font-size: 14px; white-space: nowrap;
      &:hover, &.active { color: #409eff; } }
  }
  .search-bar { flex: 1; max-width: 380px; }
  .nav-actions { display: flex; align-items: center; gap: 16px; margin-left: auto; flex-shrink: 0;
    .nav-item { color: #606266; text-decoration: none; font-size: 14px; white-space: nowrap;
      &:hover { color: #409eff; } }
    .register-btn { color: #409eff; font-weight: 500; }
    .nav-icon { color: #606266; display: flex; }
    .user-dropdown { display: flex; align-items: center; gap: 8px; cursor: pointer; outline: none;
      .user-name { font-size: 14px; color: #303133; max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    }
  }
  @media (max-width: 900px) {
    .nav-links { display: none; }
    .search-bar { max-width: none; }
  }
}

.main-content { flex: 1; padding: 24px 0 40px; }
.footer { background: #f8f9fa; padding: 24px 0; text-align: center; color: #909399; font-size: 13px; border-top: 1px solid #e4e7ed; }
</style>
