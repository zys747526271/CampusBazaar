<script setup>
import AppIcon from '@/components/ui/AppIcon.vue'

const year = new Date().getFullYear()
const columns = [
  {
    title: '买家服务',
    links: [
      { label: '全部商品', to: '/products' },
      { label: '我的订单', to: '/orders' },
      { label: '我的收藏', to: '/favorites' },
      { label: '浏览记录', to: '/history' }
    ]
  },
  {
    title: '卖家服务',
    links: [
      { label: '开通卖家', to: '/seller' },
      { label: '发布商品', to: '/seller/products/new' },
      { label: '收到的订单', to: '/seller/orders' },
      { label: '经营数据', to: '/seller' }
    ]
  },
  {
    title: '关于平台',
    links: [
      { label: '交易规则', to: '/products' },
      { label: '隐私说明', to: '/products' },
      { label: '举报入口', to: '/products' },
      { label: '管理后台', to: '/admin/login' }
    ]
  }
]
</script>

<template>
  <footer class="site-footer">
    <div class="container footer-main">
      <div class="brand">
        <div class="logo">
          <span class="logo-mark"><AppIcon name="shop" :size="18" /></span>
          <strong>校园集市</strong>
        </div>
        <p class="desc">
          面向单一高校的校内 C2C 二手交易平台。教材、数码、宿舍好物，
          同校自提、当面验货，交易全程留痕。
        </p>
        <div class="badges">
          <span class="tag tag-line"><AppIcon name="shield" :size="12" /> 校内实名</span>
          <span class="tag tag-line"><AppIcon name="map-pin" :size="12" /> 当面自提</span>
          <span class="tag tag-line"><AppIcon name="file-text" :size="12" /> 订单留痕</span>
        </div>
      </div>

      <div v-for="column in columns" :key="column.title" class="column">
        <h4>{{ column.title }}</h4>
        <RouterLink v-for="link in column.links" :key="link.label" :to="link.to">{{ link.label }}</RouterLink>
      </div>

      <div class="column contact">
        <h4>联系我们</h4>
        <p><AppIcon name="message" :size="14" /> 校园集市运营组</p>
        <p><AppIcon name="clock" :size="14" /> 工作日 9:00 - 18:00</p>
        <p><AppIcon name="map-pin" :size="14" /> 学生活动中心 302</p>
      </div>
    </div>

    <div class="container footer-bottom">
      <span>© {{ year }} CampusBazaar · 校园集市</span>
      <span class="text-muted">本站为校内二手交易演示项目，交易请当面验货，谨防诈骗。</span>
    </div>
  </footer>
</template>

<style scoped>
.site-footer { margin-top: 56px; background: #fff; border-top: 1px solid var(--line); }
.footer-main {
  display: grid; grid-template-columns: 1.6fr repeat(4, 1fr);
  gap: 32px; padding: 44px 0 32px;
}
.brand .logo { display: flex; align-items: center; gap: 9px; font-size: 16px; }
.logo-mark {
  width: 32px; height: 32px; border-radius: 10px;
  background: linear-gradient(135deg, var(--brand-light), var(--brand));
  color: #fff; display: grid; place-items: center;
}
.desc { margin-top: 12px; color: var(--muted); font-size: 13px; line-height: 1.8; max-width: 320px; }
.badges { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }

.column h4 { font-size: 13px; margin-bottom: 12px; color: var(--ink); }
.column a {
  display: block; color: var(--muted); font-size: 13px; padding: 4px 0;
}
.column a:hover { color: var(--brand); }
.contact p { display: flex; align-items: center; gap: 7px; color: var(--muted); font-size: 13px; padding: 4px 0; }

.footer-bottom {
  display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  padding: 16px 0 20px; border-top: 1px solid var(--line);
  color: var(--muted); font-size: 12px;
}

@media (max-width: 960px) {
  .footer-main { grid-template-columns: repeat(2, 1fr); gap: 24px; padding: 32px 0 20px; }
  .brand { grid-column: 1 / -1; }
}
</style>
