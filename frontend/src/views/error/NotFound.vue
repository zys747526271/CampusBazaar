<script setup>
import { useRouter } from 'vue-router'
import AppIcon from '@/components/ui/AppIcon.vue'

const router = useRouter()
</script>

<template>
  <div class="not-found">
    <div class="code">404</div>
    <h1>页面走丢了</h1>
    <p class="text-muted">
      你访问的页面可能已下架、被删除，或者链接有误。
    </p>
    <div class="ops">
      <button class="btn btn-primary" type="button" @click="router.push('/')">回到首页</button>
      <button class="btn" type="button" @click="router.push('/products')">去逛逛商品</button>
    </div>
    <div class="hint">
      <AppIcon name="info" :size="14" />
      <span>如果你是卖家，可前往卖家中心检查该商品是否仍在售。</span>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  min-height: calc(100vh - 220px);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; text-align: center; padding: 60px 24px;
}
.code {
  font-size: 96px; font-weight: 800; line-height: 1;
  letter-spacing: -4px;
  background: linear-gradient(135deg, #ffb08a, #ff5000);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
h1 { font-size: 22px; }
.ops { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; justify-content: center; }
.hint {
  margin-top: 18px; display: inline-flex; align-items: center; gap: 6px;
  color: var(--muted); font-size: 12.5px;
}
</style>
