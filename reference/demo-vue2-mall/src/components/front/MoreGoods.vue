<template>
  <div class="more-goods">
    <h1>{{ type === 'liketimes' ? '更多推荐商品' : '更多热销商品' }}</h1>
    <div class="goods-list">
      <div
        class="goods-card"
        v-for="(goods, index) in goodsList"
        :key="index"
        @click="goodsDetail(goods.id)"
        :class="{ 'out-of-stock': goods.contains === 0 }"
      >
        <img :src="goods.image | imageFliter" :alt="goods.name" />
        <p class="name">{{ goods.name }}</p>
        <p class="price">${{ goods.sellPrice }}</p>
        <span class="stock" v-if="goods.contains === 0">缺货</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MoreGoods',
  data() {
    return {
      type: '',
      goodsList: []
    };
  },
  created() {
    this.type = this.$route.query.type;
    this.fetchMoreGoods();
  },
  methods: {
    fetchMoreGoods() {
      const url = this.type === 'liketimes' ? '/api/goods/recommend/liketimes' : '/api/goods/recommend/buytimes';
      this.$axios.get(url)
        .then(res => {
          if (res.data.code === 200) {
            this.goodsList = res.data.data.data || [];
          }
        })
        .catch(err => {
          console.error("加载更多商品失败:", err);
        });
    },
    goodsDetail(id) {
      this.$router.push({
        path: "/goods/detail",
        name: "GoodsDetail",
        params: { "_id": id }
      });
    }
  }
};
</script>

<style scoped>
.more-goods {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.goods-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
}

/* 复用主页的 goods-card 样式 */
</style>
