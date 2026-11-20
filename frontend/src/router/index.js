import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layout/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', name: 'Home', component: () => import('../views/home/HomePage.vue'), meta: { title: '首页' } },
      { path: 'products', name: 'ProductList', component: () => import('../views/product/ProductList.vue'), meta: { title: '全部商品' } },
      { path: 'products/:id', name: 'ProductDetail', component: () => import('../views/product/ProductDetail.vue'), meta: { title: '商品详情' } },
      { path: 'cart', name: 'Cart', component: () => import('../views/cart/CartPage.vue'), meta: { title: '购物车', requiresAuth: true } },
      { path: 'orders', name: 'Orders', component: () => import('../views/order/OrderList.vue'), meta: { title: '我的订单', requiresAuth: true } },
      { path: 'orders/:id', name: 'OrderDetail', component: () => import('../views/order/OrderDetail.vue'), meta: { title: '订单详情', requiresAuth: true } },
      { path: 'favorites', name: 'Favorites', component: () => import('../views/user/Favorites.vue'), meta: { title: '我的收藏', requiresAuth: true } },
      { path: 'history', name: 'History', component: () => import('../views/user/History.vue'), meta: { title: '浏览记录', requiresAuth: true } },
      { path: 'profile', name: 'Profile', component: () => import('../views/user/UserProfile.vue'), meta: { title: '个人中心', requiresAuth: true } },
      {
        path: 'seller',
        name: 'SellerCenter',
        component: () => import('../views/seller/SellerCenter.vue'),
        meta: { title: '卖家中心', requiresAuth: true, requiresSeller: true }
      }
    ]
  },
  {
    path: '/auth',
    children: [
      { path: 'login', name: 'Login', component: () => import('../views/auth/LoginPage.vue'), meta: { title: '登录' } },
      { path: 'register', name: 'Register', component: () => import('../views/auth/RegisterPage.vue'), meta: { title: '注册' } }
    ]
  },
  // 管理员独立入口：不在任何用户端页面暴露链接，只能手动访问 /admin/login
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: () => import('../views/auth/AdminLogin.vue'),
    meta: { title: '管理员登录' }
  },
  {
    path: '/admin/register',
    name: 'AdminRegister',
    component: () => import('../views/auth/AdminRegister.vue'),
    meta: { title: '管理员注册' }
  },
  {
    path: '/admin',
    component: () => import('../layout/AdminLayout.vue'),
    meta: { requiresAdmin: true },
    children: [
      { path: '', name: 'AdminDashboard', component: () => import('../views/admin/Dashboard.vue'), meta: { title: '管理控制台', requiresAdmin: true } },
      { path: 'users', name: 'AdminUsers', component: () => import('../views/admin/UserManagement.vue'), meta: { title: '用户管理', requiresAdmin: true } },
      { path: 'products', name: 'AdminProducts', component: () => import('../views/admin/ProductManagement.vue'), meta: { title: '商品管理', requiresAdmin: true } },
      { path: 'sellers', name: 'AdminSellers', component: () => import('../views/admin/SellerManagement.vue'), meta: { title: '商家管理', requiresAdmin: true } },
      { path: 'comments', name: 'AdminComments', component: () => import('../views/admin/CommentManagement.vue'), meta: { title: '评论管理', requiresAdmin: true } },
      { path: 'orders', name: 'AdminOrders', component: () => import('../views/admin/OrderManagement.vue'), meta: { title: '订单管理', requiresAdmin: true } }
    ]
  },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('../views/error/NotFound.vue'), meta: { title: '页面不存在' } }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 校园集市` : '校园集市'
  const token = localStorage.getItem('token')
  const adminToken = localStorage.getItem('admin_token')

  if (to.meta.requiresAdmin) {
    if (!adminToken) {
      next({ name: 'AdminLogin', query: { redirect: to.fullPath } })
    } else {
      next()
    }
  } else if (to.meta.requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.requiresSeller && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.requiresSeller) {
    // 卖家身份以服务端为准；未开通者进入卖家中心后由页面展示开通引导
    next()
  } else {
    next()
  }
})

export default router
