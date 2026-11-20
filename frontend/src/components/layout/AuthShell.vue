<script setup>
import AppIcon from '@/components/ui/AppIcon.vue'

defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' }
})

const highlights = [
  { icon: 'shield', title: '同校实名', desc: '只和同校同学交易，身份可追溯' },
  { icon: 'map-pin', title: '当面自提', desc: '约在图书馆、宿舍楼下，省运费' },
  { icon: 'file-text', title: '全程留痕', desc: '下单、付款、发货、评价都有记录' }
]
</script>

<template>
  <div class="container auth-page">
    <aside class="aside">
      <div class="brand">
        <span class="brand-mark"><AppIcon name="shop" :size="20" /></span>
        <div>
          <strong>校园集市</strong>
          <small>CampusBazaar</small>
        </div>
      </div>
      <h2>让闲置<br />找到下一个主人</h2>
      <p class="aside-desc">教材、数码、宿舍好物，同校面交，价格实在，交易有保障。</p>

      <ul class="highlights">
        <li v-for="item in highlights" :key="item.title">
          <span class="hl-icon"><AppIcon :name="item.icon" :size="17" /></span>
          <div>
            <strong>{{ item.title }}</strong>
            <small>{{ item.desc }}</small>
          </div>
        </li>
      </ul>

      <div class="aside-foot">
        <div class="avatars">
          <span>林</span><span>陈</span><span>苏</span><span>+</span>
        </div>
        <p>已有 1,200+ 位同学在这里完成交易</p>
      </div>
    </aside>

    <section class="form-panel">
      <header class="form-head">
        <h1>{{ title }}</h1>
        <p v-if="subtitle" class="text-sm text-muted">{{ subtitle }}</p>
      </header>
      <slot />
    </section>
  </div>
</template>

<style scoped>
.auth-page {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 0; margin: 28px auto 40px;
  background: #fff; border: 1px solid var(--line); border-radius: 20px;
  overflow: hidden; min-height: 560px;
  box-shadow: 0 18px 48px rgba(16, 24, 40, .06);
}

.aside {
  position: relative; padding: 40px 44px;
  background: linear-gradient(150deg, #1f2329, #2c3138 55%, #3d2a20);
  color: #fff; display: flex; flex-direction: column;
  overflow: hidden;
}
.aside::before {
  content: ''; position: absolute; right: -80px; top: -80px;
  width: 320px; height: 320px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 122, 69, .38), transparent 65%);
}
.aside::after {
  content: ''; position: absolute; left: -60px; bottom: -100px;
  width: 260px; height: 260px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 80, 0, .22), transparent 65%);
}
.brand { display: flex; align-items: center; gap: 10px; position: relative; }
.brand-mark {
  width: 38px; height: 38px; border-radius: 11px;
  background: linear-gradient(135deg, var(--brand-light), var(--brand));
  display: grid; place-items: center;
}
.brand strong { display: block; font-size: 16px; }
.brand small { font-size: 10.5px; letter-spacing: .14em; color: rgba(255, 255, 255, .55); }

.aside h2 {
  position: relative; margin-top: 44px;
  font-size: 32px; line-height: 1.35; letter-spacing: -.5px;
}
.aside-desc { position: relative; margin-top: 14px; color: rgba(255, 255, 255, .68); font-size: 13.5px; line-height: 1.8; max-width: 320px; }

.highlights { position: relative; margin-top: 30px; display: flex; flex-direction: column; gap: 14px; }
.highlights li { display: flex; align-items: center; gap: 12px; }
.hl-icon {
  width: 34px; height: 34px; border-radius: 10px; flex: none;
  display: grid; place-items: center;
  background: rgba(255, 255, 255, .1); color: #ffb38a;
}
.highlights strong { display: block; font-size: 13.5px; }
.highlights small { color: rgba(255, 255, 255, .58); font-size: 11.5px; }

.aside-foot { position: relative; margin-top: auto; padding-top: 28px; }
.avatars { display: flex; }
.avatars span {
  width: 28px; height: 28px; border-radius: 50%; margin-right: -8px;
  display: grid; place-items: center; font-size: 11px; font-weight: 700;
  background: linear-gradient(135deg, #ffd9c7, #ffb08a); color: #a03c0d;
  border: 2px solid #2c3138;
}
.aside-foot p { margin-top: 12px; font-size: 11.5px; color: rgba(255, 255, 255, .55); }

.form-panel { padding: 44px 56px; display: flex; flex-direction: column; justify-content: center; }
.form-head { margin-bottom: 24px; }
.form-head h1 { font-size: 26px; letter-spacing: -.5px; }
.form-head p { margin-top: 6px; }

@media (max-width: 900px) {
  .auth-page { grid-template-columns: 1fr; min-height: auto; }
  .aside { display: none; }
  .form-panel { padding: 28px 22px 32px; }
  .form-head h1 { font-size: 22px; }
}
</style>
