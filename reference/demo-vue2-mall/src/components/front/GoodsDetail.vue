<template>
  <div id="goods-detail">
    <nav-bar
      :active-route="activeRoute"
      :is-logged-in="isLoggedIn"
      :username="username"
      :show-search-bar="true"
      @open-loading="openLoading"
      @close-loading="closeLoading"
    />
    <div class="main-content" v-if="loaded">
      <div class="goods-container" v-if="goods.name">
        <div class="goods-images">
          <el-carousel height="400px" :interval="5000" arrow="hover">
            <el-carousel-item v-for="(img, index) in goodsImages" :key="index">
              <div class="image-wrapper">
                <img :src="img" alt="商品图片" class="carousel-image" />
              </div>
            </el-carousel-item>
          </el-carousel>
        </div>
        <div class="goods-info">
          <h1>{{ goods.name }}</h1>
          <p class="price">
            <span class="sell-price">¥{{ goods.sellPrice || '未提供' }}</span>
            <span
              class="origin-price"
              v-if="goods.originPrice && goods.originPrice > goods.sellPrice"
            >
              原价: ¥{{ goods.originPrice }}
            </span>
          </p>
          <p class="stock">库存: {{ goods.contains !== undefined ? goods.contains : '未提供' }} 件</p>
          <p class="intro">{{ goods.intro || '暂无简介' }}</p>
          <p class="address">生产地: {{ goods.createAddress_id || '未知' }}</p>
          <p class="address">发货地: {{ goods.sendAddress_id || '未知' }}</p>
          <div class="actions">
            <el-input-number
              v-model="quantity"
              :min="1"
              :max="goods.contains || 1"
              size="small"
              :disabled="goods.contains === 0"
            />
            <el-button
              type="primary"
              @click="addToCart"
              :disabled="!isLoggedIn || goods.contains === 0"
            >
              加入购物车
            </el-button>
            <el-button
              type="danger"
              @click="buyNow"
              :disabled="!isLoggedIn || goods.contains === 0"
            >
              立即购买
            </el-button>
          </div>
        </div>
      </div>
      <el-empty v-else description="商品数据未加载，请刷新重试" class="error-container" />

      <!-- 推荐商品 -->
      <div class="recommend-container">
        <h2>可能感兴趣的商品</h2>
        <div class="recommend-list" v-if="similarGoods.length">
          <div
            v-for="item in similarGoods"
            :key="item._id"
            class="recommend-item"
            @click="goToGoods(item._id)"
          >
            <img :src="item.image" alt="推荐商品" />
            <p>{{ item.name }}</p>
            <span>¥{{ item.sellPrice }}</span>
          </div>
        </div>
        <p v-else>暂无推荐商品</p>
      </div>

      <!-- 评论区域（保留接口） -->
      <div class="comments-container">
        <h2>用户评论</h2>
        <div class="comment-list" v-if="comments.length">
          <div v-for="comment in comments" :key="comment._id" class="comment-item">
            <p><strong>{{ comment.userName }}</strong> - {{ comment.createTime }}</p>
            <el-rate :value="comment.points" disabled />
            <p>{{ comment.content }}</p>
          </div>
        </div>
        <p v-else>暂无评论</p>
      </div>
    </div>
    <div v-else class="loading-container">
      <p v-if="error">{{ error }}</p>
      <p v-else>加载中...</p>
    </div>
  </div>
</template>

<script>
import NavBar from './NavBar.vue';

export default {
  name: 'GoodsDetail',
  components: { NavBar },
  data() {
    return {
      goods: {},
      goodsImages: [],
      similarGoods: [],
      comments: [],
      quantity: 1,
      isLoggedIn: false,
      username: '',
      userId: null,
      activeRoute: this.$route.path,
      loaded: false,
      error: null,
      loading: null,
      backendBaseUrl: 'http://127.0.0.1:5000', // 后端基础地址
    };
  },
  created() {
    const _id = this.$route.params._id;
    if (!_id) {
      this.error = '无效的商品ID';
      this.loaded = true;
      return;
    }
    this.loadGoods(_id);
    this.checkLoginStatus();
  },
  watch: {
    '$route'(to) {
      this.activeRoute = to.path;
      const _id = to.params._id;
      if (_id) {
        this.loaded = false;
        this.error = null;
        this.loadGoods(_id);
      }
    },
  },
  methods: {
    goToGoods(id) {
      this.$router.push(`/goods/${id}`);
    },
    loadGoods(_id) {
      this.openLoading('加载商品详情...');
      Promise.all([
        this.$axios.get(`/api/goods/detail/${_id}`),
        this.$axios.get(`/api/comment/${_id}`),
      ])
        .then(([goodsRes, commentsRes]) => {
          this.closeLoading();

          if (goodsRes.data.code === 200) {
            this.goods = goodsRes.data.data;
            this.goodsImages = this.goods.images
              ? JSON.parse(this.goods.images).map((img) => `${this.backendBaseUrl}${img}`)
              : [this.goods.image || 'https://via.placeholder.com/300'];
            this.quantity = this.goods.contains > 0 ? 1 : 0;

            this.loadRecommendations();
          } else {
            this.error = goodsRes.data.info || '加载商品详情失败';
          }

          if (commentsRes.data.code === 200) {
            const commentData = commentsRes.data.data.data || [];
            this.comments = commentData.map((c) => ({
              ...c,
              userName: c.userName || '匿名用户',
              createTime: new Date(c.createTime).toLocaleString(),
            }));
          }

          this.loaded = true;
        })
        .catch((err) => {
          this.closeLoading();
          this.error = '加载失败，请稍后重试';
          this.loaded = true;
          console.error('加载错误:', err);
        });
    },
    loadRecommendations() {
      if (!this.goods._id || !this.goods.goodsType_id) return;
      this.$axios
        .post('/api/recommend/goods', {
          tagId: this.goods.goodsType_id,
          goodsId: this.goods._id,
          limit: 4,
        })
        .then((res) => {
          console.log('推荐商品响应:', res.data);
          if (res.data.code === 200) {
            this.similarGoods = (res.data.data.data || []).map((item) => ({
              ...item,
              image: `${this.backendBaseUrl}${item.image}`,
            }));
          } else {
            this.$message.warning(res.data.info || '加载推荐商品失败');
          }
        })
        .catch((err) => {
          console.error('推荐商品加载失败:', err);
          this.$message.error('加载推荐商品失败，请稍后重试');
        });
    },
    addToCart() {
      if (!this.isLoggedIn) {
        this.$message.warning('请先登录');
        this.$router.push('/login');
        return;
      }
      if (!this.goods._id) {
        this.$message.error('商品数据未加载，无法加入购物车');
        return;
      }
      this.openLoading('加入购物车...');
      this.$axios
        .post('/api/add/goods/2/court', 
          { goodsId: this.goods._id, quantity: this.quantity },
          { headers: { 'Content-Type': 'application/json' } }
        )
        .then((res) => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.$message.success(res.data.info || '已加入购物车');
          } else {
            this.$message.error(res.data.info || '加入失败');
          }
        })
        .catch((err) => {
          this.closeLoading();
          this.$message.error('加入购物车失败');
          console.error('加入购物车错误:', err);
        });
    },
    buyNow() {
      if (!this.isLoggedIn) {
        this.$message.warning('请先登录');
        this.$router.push('/login');
        return;
      }
      if (!this.goods._id || this.goods.sellPrice === undefined) {
        this.$message.error('商品数据未加载，无法购买');
        return;
      }
      this.openLoading('处理订单...');
      const payValue = this.goods.sellPrice * this.quantity;
      this.$axios
        .post('/api/buy/goods', {
          payValue: payValue,
          goodsList: JSON.stringify([{ id: this.goods._id, number: this.quantity }]),
          address: '用户默认地址',
        })
        .then((res) => {
          this.closeLoading();
          if (res.data.code === 200) {
            this.$message.success('购买成功');
            this.$router.push('/receipt');
          } else {
            this.$message.error(res.data.info || '购买失败');
          }
        })
        .catch((err) => {
          this.closeLoading();
          this.$message.error('购买失败');
          console.error('购买错误:', err);
        });
    },
    checkLoginStatus() {
      this.userId = sessionStorage.getItem('_id');
      this.isLoggedIn = !!this.userId;
      if (this.isLoggedIn) {
        this.$axios
          .get('/api/self')
          .then((res) => {
            if (res.data.code === 200) {
              this.username = res.data.data.name || '用户';
            }
          })
          .catch((err) => console.error('获取用户信息失败:', err));
      }
    },
    openLoading(text) {
      this.loading = this.$loading({
        lock: true,
        text,
        spinner: 'el-icon-loading',
        background: 'rgba(0, 0, 0, 0.7)',
      });
    },
    closeLoading() {
      if (this.loading) this.loading.close();
    },
  },
};
</script>

<style scoped>
#goods-detail {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.main-content {
  max-width: 1200px;
  margin: 70px auto 0;
}

.goods-container {
  display: flex;
  gap: 20px;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.goods-images {
  flex: 1;
  max-width: 500px;
}

.el-carousel {
  width: 100%;
  height: 400px;
}

.image-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f0f0f0;
}

.carousel-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 8px;
}

.goods-info {
  flex: 1;
  padding: 10px;
}

.goods-info h1 {
  font-size: 24px;
  margin: 0 0 15px;
  color: #333;
}

.price {
  margin: 15px 0;
}

.sell-price {
  font-size: 28px;
  color: #ff4444;
  font-weight: bold;
}

.origin-price {
  font-size: 16px;
  color: #999;
  text-decoration: line-through;
  margin-left: 10px;
}

.stock {
  color: #666;
  margin: 10px 0;
}

.intro {
  color: #333;
  line-height: 1.6;
  margin: 15px 0;
  background: #fafafa;
  padding: 10px;
  border-radius: 4px;
}

.address {
  color: #666;
  margin: 5px 0;
}

.actions {
  margin-top: 20px;
  display: flex;
  gap: 15px;
  align-items: center;
}

.el-button {
  border-radius: 4px;
  padding: 12px 20px;
}

.el-button[type="primary"] {
  background: #409eff;
  border-color: #409eff;
}

.el-button[type="danger"] {
  background: #ff4444;
  border-color: #ff4444;
}

.recommend-container,
.comments-container {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.recommend-container h2,
.comments-container h2 {
  font-size: 20px;
  color: #333;
  margin-bottom: 15px;
}

.recommend-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

.recommend-item {
  text-align: center;
  cursor: pointer;
  transition: transform 0.2s;
}

.recommend-item:hover {
  transform: translateY(-5px);
}

.recommend-item img {
  width: 100%;
  height: 150px;
  object-fit: contain; /* 改为 contain，确保图片完整显示 */
  border-radius: 8px;
  background: #f0f0f0; /* 添加背景色，填充空白区域 */
}

.recommend-item p {
  margin: 8px 0;
  font-size: 14px;
  color: #333;
}

.recommend-item span {
  color: #ff4444;
  font-size: 16px;
  font-weight: bold;
}

.comment-list {
  margin-top: 20px;
}

.comment-item {
  padding: 15px 0;
  border-bottom: 1px solid #eee;
}

.comment-item p {
  margin: 5px 0;
  color: #666;
}

.loading-container,
.error-container {
  text-align: center;
  padding: 50px;
  color: #666;
}

@media (max-width: 768px) {
  .goods-container {
    flex-direction: column;
  }

  .goods-images {
    max-width: 100%;
  }

  .actions {
    flex-direction: column;
    gap: 10px;
  }

  .el-button {
    width: 100%;
  }
}
</style>
