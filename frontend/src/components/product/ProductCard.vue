<script setup>
import { computed } from 'vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppImage from '@/components/ui/AppImage.vue'
import AppRating from '@/components/ui/AppRating.vue'
import { deliveryLabels, money, relativeTime } from '@/utils/format'

const props = defineProps({
  product: { type: Object, required: true },
  showSeller: { type: Boolean, default: true },
  showFavorite: { type: Boolean, default: false },
  favorited: { type: Boolean, default: false }
})
const emit = defineEmits(['favorite', 'click'])

const soldOut = computed(() => !props.product.is_on_sale)
const seller = computed(() => props.product.seller || {})
const sellerName = computed(() => seller.value.nickname || '校内同学')
const initial = computed(() => sellerName.value.slice(0, 1))
const discountText = computed(() => {
  const value = Number(props.product.discount || 0)
  return value > 0 && value < 10 ? `${value.toFixed(1)} 折` : ''
})

const onFavorite = (event) => {
  event.preventDefault()
  event.stopPropagation()
  emit('favorite', props.product)
}
</script>

<template>
  <RouterLink
    :to="`/products/${product.id}`"
    class="product-card"
    :class="{ 'is-sold-out': soldOut }"
    @click="emit('click', product)"
  >
    <div class="cover">
      <AppImage :src="product.cover_image" :alt="product.name" radius="10px 10px 0 0" />
      <span v-if="discountText" class="badge-discount">{{ discountText }}</span>
      <span v-if="soldOut" class="mask"><span>已售出</span></span>
      <button
        v-if="showFavorite"
        class="fav"
        type="button"
        :class="{ on: favorited }"
        :aria-label="favorited ? '取消收藏' : '收藏'"
        @click="onFavorite"
      >
        <AppIcon name="heart" :size="16" :filled="favorited" />
      </button>
    </div>

    <div class="body">
      <h3 class="title clamp-2">{{ product.name }}</h3>
      <div class="delivery-row">
        <span v-for="label in deliveryLabels(product)" :key="label" class="deliver-tag" :class="label === '包邮' ? 'free' : ''">
          {{ label }}
        </span>
        <span v-if="product.supports_express && !product.free_shipping" class="deliver-tag fee">
          运费 ¥{{ money(product.shipping_fee) }}
        </span>
      </div>
      <div class="meta">
        <span class="tag tag-line">{{ product.condition }}</span>
        <span class="text-xs text-muted">{{ relativeTime(product.created_at) }}</span>
      </div>
      <div class="price-row">
        <span class="price price-md"><span class="unit">¥</span>{{ money(product.price) }}</span>
        <span v-if="product.original_price" class="origin">¥{{ money(product.original_price) }}</span>
        <span class="sold">已售 {{ product.sales || 0 }}</span>
      </div>

      <div v-if="showSeller" class="seller">
        <span class="avatar">
          <img v-if="seller.avatar_url" :src="seller.avatar_url" alt="" />
          <template v-else>{{ initial }}</template>
        </span>
        <span class="name ellipsis">{{ sellerName }}</span>
        <span v-if="seller.rating" class="rate">
          <AppRating :model-value="seller.rating" :size="12" readonly />
        </span>
        <span v-else class="text-xs text-muted">新卖家</span>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.product-card {
  display: flex; flex-direction: column;
  background: #fff; border: 1px solid var(--line); border-radius: 10px;
  overflow: hidden; transition: transform .18s, box-shadow .18s, border-color .18s;
}
.product-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(16, 24, 40, .1);
  border-color: transparent;
}
.cover { position: relative; }
.badge-discount {
  position: absolute; left: 10px; top: 10px;
  background: rgba(31, 35, 41, .82); color: #fff;
  font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 5px;
  backdrop-filter: blur(4px);
}
.mask {
  position: absolute; inset: 0;
  background: rgba(255, 255, 255, .62);
  display: grid; place-items: center;
  backdrop-filter: blur(1px);
}
.mask span {
  background: rgba(31, 35, 41, .78); color: #fff;
  padding: 5px 14px; border-radius: 999px; font-size: 12.5px;
}
.fav {
  position: absolute; right: 8px; top: 8px;
  width: 30px; height: 30px; border-radius: 50%;
  border: none; background: rgba(255, 255, 255, .92);
  color: var(--muted); display: grid; place-items: center;
  box-shadow: var(--shadow-xs);
  opacity: 0; transform: translateY(-2px); transition: all .16s;
}
.product-card:hover .fav { opacity: 1; transform: none; }
.fav.on { color: var(--brand); opacity: 1; }

.body { padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.title { font-size: 14px; font-weight: 500; line-height: 1.5; min-height: 42px; color: var(--ink); }
.delivery-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.deliver-tag {
  font-size: 11px; line-height: 1; padding: 4px 6px; border-radius: 4px;
  color: #475467; background: #f2f4f7;
}
.deliver-tag.free { color: #0f7b57; background: #e7f7f0; }
.deliver-tag.fee { color: #b54708; background: #fff4e5; }
.meta { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.price-row { display: flex; align-items: baseline; gap: 8px; margin-top: auto; }
.origin { color: var(--muted-2); font-size: 12px; text-decoration: line-through; }
.sold { margin-left: auto; color: var(--muted); font-size: 11.5px; }

.seller {
  display: flex; align-items: center; gap: 6px;
  padding-top: 10px; border-top: 1px dashed var(--line);
  color: var(--muted); font-size: 12px;
}
.avatar {
  width: 20px; height: 20px; border-radius: 50%; flex: none;
  display: grid; place-items: center; font-size: 10px; font-weight: 700;
  background: linear-gradient(135deg, #ffe2d3, #ffc3a6); color: #a03c0d;
  overflow: hidden;
}
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.name { max-width: 76px; }
.rate { margin-left: auto; }
.is-sold-out .title { color: var(--muted); }
</style>
