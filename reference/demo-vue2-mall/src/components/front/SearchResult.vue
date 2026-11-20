<template>
  <div class="search-result">
    <h1>搜索结果：{{ keyword }}</h1>
    <div class="goods-list">
      <div
        class="goods-card"
        v-for="(goods, index) in searchResults"
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
  name: 'SearchResult',
  data() {
    return {
      keyword: '',
      searchResults: []
    };
  },
  created() {
    this.keyword = this.$route.query.keyword;
    this.searchGoods();
  },
  methods: {
    searchGoods() {
      this.$axios.post("/api/goods/search", { keyWord: this.keyword })
        .then(res => {
          if (res.data.code === 200) {
            this.searchResults = res.data.data.data || [];
            if (this.searchResults.length === 0) {
              this.$message.info("未找到相关商品，显示全部商品");
              this.fetchAllGoods();
            }
          }
        })
        .catch(err => {
          console.error("搜索失败:", err);
          this.fetchAllGoods();
        });
    },
    fetchAllGoods() {
      this.$axios.post("/api/goods", { start: 0, nums: 50 })
        .then(res => {
          if (res.data.code === 200) {
            this.searchResults = res.data.data.data || [];
          }
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
.search-result {
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
