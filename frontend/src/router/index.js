import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/ShopLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('@/views/home/HomeView.vue') },
      { path: 'products', name: 'products', component: () => import('@/views/product/ProductListView.vue') },
      { path: 'products/:id', name: 'product-detail', component: () => import('@/views/product/ProductDetailView.vue') },
      { path: 'shops/:id', name: 'shop', component: () => import('@/views/shop/ShopView.vue') },
      {
        path: 'cart',
        name: 'cart',
        component: () => import('@/views/cart/CartView.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'checkout',
        name: 'checkout',
        component: () => import('@/views/checkout/CheckoutView.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'orders',
        component: () => import('@/layouts/AccountLayout.vue'),
        meta: { requiresAuth: true },
        children: [
          { path: '', name: 'orders', component: () => import('@/views/order/OrderListView.vue') },
          { path: ':id', name: 'order-detail', component: () => import('@/views/order/OrderDetailView.vue') }
        ]
      },
      {
        path: '',
        component: () => import('@/layouts/AccountLayout.vue'),
        meta: { requiresAuth: true },
        children: [
          { path: 'profile', name: 'profile', component: () => import('@/views/user/ProfileView.vue') },
          { path: 'favorites', name: 'favorites', component: () => import('@/views/user/FavoritesView.vue') },
          { path: 'history', name: 'history', component: () => import('@/views/user/HistoryView.vue') },
          { path: 'addresses', name: 'addresses', component: () => import('@/views/user/AddressView.vue') },
          { path: 'messages', name: 'messages', component: () => import('@/views/user/MessageView.vue') },
          { path: 'balance', name: 'balance', component: () => import('@/views/user/BalanceView.vue') }
        ]
      },
      { path: 'login', name: 'login', component: () => import('@/views/auth/LoginView.vue'), meta: { guestOnly: true } },
      { path: 'register', name: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { guestOnly: true } },
      { path: 'forgot', name: 'forgot', component: () => import('@/views/auth/ForgotView.vue'), meta: { guestOnly: true } },
      { path: ':pathMatch(.*)*', name: 'not-found', component: () => import('@/views/error/NotFound.vue') }
    ]
  },
  {
    path: '/seller',
    component: () => import('@/layouts/SellerLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'seller', component: () => import('@/views/seller/SellerDashboard.vue') },
      { path: 'products', name: 'seller-products', component: () => import('@/views/seller/SellerProducts.vue') },
      { path: 'products/new', name: 'seller-product-new', component: () => import('@/views/seller/SellerProductForm.vue') },
      { path: 'products/:id/edit', name: 'seller-product-edit', component: () => import('@/views/seller/SellerProductForm.vue') },
      { path: 'orders', name: 'seller-orders', component: () => import('@/views/seller/SellerOrders.vue') },
      { path: 'categories', name: 'seller-categories', component: () => import('@/views/seller/SellerCategories.vue') },
      { path: 'reviews', name: 'seller-reviews', component: () => import('@/views/seller/SellerReviews.vue') }
    ]
  },
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('@/views/admin/AdminLogin.vue'),
    meta: { adminGuestOnly: true }
  },
  {
    path: '/admin/register',
    name: 'admin-register',
    component: () => import('@/views/admin/AdminRegister.vue'),
    meta: { adminGuestOnly: true }
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAdmin: true },
    children: [
      { path: '', name: 'admin-dashboard', component: () => import('@/views/admin/AdminDashboard.vue') },
      { path: 'users', name: 'admin-users', component: () => import('@/views/admin/AdminUsers.vue') },
      { path: 'sellers', name: 'admin-sellers', component: () => import('@/views/admin/AdminSellers.vue') },
      { path: 'products', name: 'admin-products', component: () => import('@/views/admin/AdminProducts.vue') },
      { path: 'comments', name: 'admin-comments', component: () => import('@/views/admin/AdminComments.vue') },
      { path: 'orders', name: 'admin-orders', component: () => import('@/views/admin/AdminOrders.vue') },
      { path: 'tags', name: 'admin-tags', component: () => import('@/views/admin/AdminTags.vue') },
      { path: 'banners', name: 'admin-banners', component: () => import('@/views/admin/AdminBanners.vue') },
      { path: 'reports', name: 'admin-reports', component: () => import('@/views/admin/AdminReports.vue') },
      { path: 'audit', name: 'admin-audit', component: () => import('@/views/admin/AdminAudit.vue') }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return { top: 0 }
  }
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.requiresAdmin) {
    if (!auth.isAdmin) return { path: '/admin/login', query: { redirect: to.fullPath } }
    try {
      await auth.fetchAdmin()
    } catch (error) {
      if (error.status === 401 || error.status === 403) return { path: '/admin/login', query: { redirect: to.fullPath } }
    }
    return true
  }

  if (to.meta.adminGuestOnly && auth.isAdmin) {
    return '/admin'
  }

  if (to.meta.requiresAuth) {
    if (!auth.isLoggedIn) return { path: '/login', query: { redirect: to.fullPath } }
    try {
      await auth.fetchProfile()
    } catch (error) {
      if (error.status === 401) return { path: '/login', query: { redirect: to.fullPath } }
    }
    return true
  }

  if (to.meta.guestOnly && auth.isLoggedIn) {
    return typeof to.query.redirect === 'string' && to.query.redirect.startsWith('/') ? to.query.redirect : '/'
  }

  if (auth.isLoggedIn && !auth.user) {
    // 已登录但刷新后还没拿到资料：静默补齐，失败不阻塞浏览
    try {
      await auth.fetchProfile()
    } catch (error) {
      /* ignore */
    }
  }
  return true
})

export default router
