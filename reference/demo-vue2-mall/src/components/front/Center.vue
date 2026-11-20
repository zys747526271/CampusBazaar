<template>
  <div id="center">
    <nav-bar
      :active-route.sync="activeRoute"
      :is-logged-in.sync="isLoggedIn"
      :username.sync="username"
      @open-loading="openLoading"
      @close-loading="closeLoading"
    >
      <template v-slot:search-bar>
        <search-bar @search="searchGoods" />
      </template>
    </nav-bar>

    <div class="main-content">
      <div class="right-content">
        <el-carousel height="400px" class="banner-carousel">
          <el-carousel-item v-for="(ad, index) in ads" :key="index">
            <img :src="ad.image | imageFilter" :alt="ad.title" @click="handleAdClick(ad)" class="banner-image" />
          </el-carousel-item>
        </el-carousel>

        <div class="section all-goods-section">
          <h2>全部商品</h2>
          <div class="goods-list">
            <div
              class="goods-card"
              v-for="(goods, index) in allGoods"
              :key="goods._id"
              @click="goodsDetail(goods._id)"
              :class="{ 'out-of-stock': goods.contains === 0 }"
            >
              <img :src="goods.image | imageFilter" :alt="goods.intro" />
              <p class="name">{{ goods.intro }}</p>
              <p class="price">${{ goods.sellPrice }}</p>
              <span class="stock" v-if="goods.contains === 0">缺货</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import NavBar from './NavBar.vue';
import SearchBar from './SearchBar.vue';

export default {
  name: 'Center',
  components: {
    NavBar,
    SearchBar,
    'el-carousel': () => import('element-ui').then(m => m.Carousel),
    'el-carousel-item': () => import('element-ui').then(m => m.CarouselItem)
  },
  created() {
    this.getAds();
    this.fetchAllGoods();
    this.checkLoginStatus();
  },
  data() {
    return {
      loading: null,
      ads: [],
      allGoods: [],
      activeRoute: this.$route.path,
      isLoggedIn: false,
      username: ''
    };
  },
  watch: {
    '$route'(to) {
      this.activeRoute = to.path;
      this.checkLoginStatus();
    }
  },
  methods: {
    openLoading(text = "加载...") {
      this.loading = this.$loading({
        lock: true,
        text: text,
        spinner: 'el-icon-loading',
        background: 'rgba(0, 0, 0, 0.7)'
      });
    },
    closeLoading() {
      if (this.loading) this.loading.close();
    },
    getAds() {
      this.$axios.get("/api/ads")
        .then(res => {
          if (res.data.code === 200) this.ads = res.data.data.data;
        })
        .catch(err => console.error("广告加载失败:", err));
    },
    fetchAllGoods() {
      this.openLoading("加载商品...");
      this.$axios.post("/api/public/goods", { start: 0, nums: 50 })
        .then(res => {
          this.closeLoading();
          console.log("Public goods response:", res.data);
          if (res.data.code === 200) {
            this.allGoods = res.data.data || [];
            const hasInactive = this.allGoods.some(g => !g.is_active);
            if (hasInactive) console.error("Inactive goods in Center:", this.allGoods.filter(g => !g.is_active));
          }
        })
        .catch(err => {
          this.closeLoading();
          console.error("获取商品失败:", err);
        });
    },
    goodsDetail(id) {
      if (!id) {
        console.error("商品 ID 未定义");
        return;
      }
      this.$router.push(`/goods/${id}`);
    },
    handleAdClick(ad) {
      console.log("点击广告:", ad);
    },
    checkLoginStatus() {
      const userId = sessionStorage.getItem('_id');
      if (!userId || userId === '') {
        this.isLoggedIn = false;
        this.username = '';
        return;
      }
      this.isLoggedIn = true;
      this.$axios.get("/api/self")
        .then(res => {
          if (res.data.code === 200) {
            this.username = res.data.data.name || '用户';
          } else {
            this.isLoggedIn = false;
            sessionStorage.removeItem('_id');
          }
        })
        .catch(err => {
          console.error("获取用户信息失败:", err);
          this.isLoggedIn = false;
          sessionStorage.removeItem('_id');
        });
    },
    searchGoods(keyword) {
      // 假设有一个搜索接口
      this.$axios.post("/api/goods/search", { keyWord: keyword })
        .then(res => {
          if (res.data.code === 200) {
            this.allGoods = res.data.data.data || [];
          }
        })
        .catch(err => console.error("搜索失败:", err));
    }
  }
};
</script>

<style scoped>
#center {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.main-content {
  margin-top: 70px;
  padding: 0 20px;
}

.right-content {
  max-width: 1200px;
  margin: 0 auto;
}

.banner-carousel {
  margin-bottom: 20px;
  border-radius: 8px;
  overflow: hidden;
}

.banner-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.section {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}

.section h2 {
  margin: 0 0 15px;
  font-size: 20px;
  color: #333;
}

.goods-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
}

.goods-card {
  padding: 10px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
}

.goods-card:hover:not(.out-of-stock) {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}

.goods-card img {
  width: 100%;
  height: 150px;
  object-fit: contain;
  border-radius: 4px;
}

.goods-card.out-of-stock img {
  filter: grayscale(100%);
  opacity: 0.7;
}

.goods-card .name {
  font-size: 14px;
  color: #333;
  margin: 5px 0;
  height: 40px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.goods-card .price {
  color: #ff4444;
  font-size: 16px;
  font-weight: bold;
  margin: 5px 0;
}

.goods-card .stock {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(255, 68, 68, 0.9);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

@media (max-width: 768px) {
  .main-content {
    margin-top: 70px;
  }
  .banner-carousel {
    height: 200px;
  }
  .goods-list {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }
}
</style>
